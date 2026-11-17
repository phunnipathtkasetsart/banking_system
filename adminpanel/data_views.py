"""Data explorer: one admin-only place to inspect both databases as stored.

- Overview: every SQL table + Mongo collection with counts, plus a rollback snapshot.
- SQL table: real columns/constraints from Postgres catalogs + raw rows (SELECT *).
- Mongo collection: stats, indexes, inferred document schema + raw JSON documents.
- Passwords: how Django stores passwords (PBKDF2 hash anatomy) with a try-it form.

Read-only. Table/collection names come from a whitelist, never from user input.
"""
from collections import defaultdict

from bson import json_util
from django import forms
from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import connection
from django.http import Http404
from django.shortcuts import render

from banking.models import Account, Beneficiary, Transaction, TransactionEntry
from core.decorators import admin_required
from core.mongo import ALL_COLLECTIONS, ACTIVITY_LOGS, get_db
from users.models import User

SQL_MODELS = [User, Account, Transaction, TransactionEntry, Beneficiary]
SQL_TABLES = {m._meta.db_table: m for m in SQL_MODELS}
ROW_LIMIT = 100
DOC_LIMIT = 50


def _fetch(sql, params=()):
    with connection.cursor() as cur:
        cur.execute(sql, params)
        cols = [c.name for c in cur.description]
        return cols, cur.fetchall()


def _sidebar():
    return {"sql_tables": list(SQL_TABLES), "collections": ALL_COLLECTIONS}


# ---------------------------------------------------------------- overview

@admin_required
def overview(request):
    db = get_db()
    sql = []
    for table, model in SQL_TABLES.items():
        sql.append({"name": table, "model": model.__name__, "rows": model.objects.count()})
    mongo = []
    for name in ALL_COLLECTIONS:
        stats = db.command("collStats", name)
        mongo.append({"name": name, "docs": stats.get("count", 0), "size": stats.get("size", 0),
                      "indexes": stats.get("nindexes", 0)})
    snapshot = {
        "accounts": Account.objects.select_related("user").order_by("id"),
        "txn_count": Transaction.objects.count(),
        "entry_count": TransactionEntry.objects.count(),
        "failed": list(db[ACTIVITY_LOGS].find({"status": "FAILED"}).sort("timestamp", -1).limit(5)),
    }
    return render(request, "adminpanel/data/overview.html",
                  {"sql": sql, "mongo": mongo, "snap": snapshot, **_sidebar()})


# ---------------------------------------------------------------- SQL table

@admin_required
def sql_table(request, table):
    if table not in SQL_TABLES:
        raise Http404("Unknown table")
    q = request.GET.get("q", "").strip()

    _, columns = _fetch(
        """SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
           FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position""",
        [table],
    )
    _, constraints = _fetch(
        """SELECT conname, contype, pg_get_constraintdef(oid)
           FROM pg_constraint WHERE conrelid = %s::regclass ORDER BY contype, conname""",
        [table],
    )
    kinds = {"p": "Primary key", "f": "Foreign key", "u": "Unique", "c": "Check"}
    constraints = [(name, kinds.get(kind, kind), definition) for name, kind, definition in constraints]

    # table name is whitelisted above; the row-as-text cast lets one ILIKE search every column
    sql = f'SELECT * FROM "{table}"'
    params = []
    if q:
        sql += f' WHERE "{table}"::text ILIKE %s'
        params.append(f"%{q}%")
    sql += f" ORDER BY 1 DESC LIMIT {ROW_LIMIT}"
    col_names, rows = _fetch(sql, params)
    total = SQL_TABLES[table].objects.count()

    return render(request, "adminpanel/data/sql_table.html", {
        "table": table, "model": SQL_TABLES[table].__name__, "columns": columns,
        "constraints": constraints, "col_names": col_names, "rows": rows, "total": total,
        "q": q, "limit": ROW_LIMIT, "query_text": sql.replace("%s", f"'%{q}%'"), **_sidebar(),
    })


# ---------------------------------------------------------------- Mongo collection

def _bson_type(value):
    if isinstance(value, bool):
        return "bool"
    return {int: "int", float: "double", str: "string", list: "array", dict: "object",
            type(None): "null"}.get(type(value), type(value).__name__)


@admin_required
def mongo_collection(request, name):
    if name not in ALL_COLLECTIONS:
        raise Http404("Unknown collection")
    coll = get_db()[name]
    field, value = request.GET.get("field", "").strip(), request.GET.get("value", "").strip()
    query = {}
    if field and value:
        # numbers typed in the box (e.g. userId=2) should match int fields
        query = {field: int(value) if value.lstrip("-").isdigit() else value}

    docs = list(coll.find(query).sort("_id", -1).limit(DOC_LIMIT))

    schema = defaultdict(set)
    for d in coll.find().limit(200):
        for k, v in d.items():
            schema[k].add(_bson_type(v))
    stats = get_db().command("collStats", name)

    return render(request, "adminpanel/data/mongo_collection.html", {
        "name": name, "total": coll.count_documents({}), "matched": coll.count_documents(query),
        "schema": sorted((k, ", ".join(sorted(t))) for k, t in schema.items()),
        "indexes": [(n, json_util.dumps(i["key"])) for n, i in coll.index_information().items()],
        "size": stats.get("size", 0), "avg": stats.get("avgObjSize", 0),
        "docs": [json_util.dumps(d, indent=2, json_options=json_util.RELAXED_JSON_OPTIONS) for d in docs],
        "field": field, "value": value, "query_text": json_util.dumps(query), "limit": DOC_LIMIT,
        "fields": sorted(schema), **_sidebar(),
    })


# ---------------------------------------------------------------- passwords

def split_hash(encoded):
    """'pbkdf2_sha256$1000000$salt$hash' -> dict of parts (unusable/unknown -> raw)."""
    parts = (encoded or "").split("$")
    if len(parts) == 4:
        algorithm, iterations, salt, digest = parts
        return {"algorithm": algorithm, "iterations": iterations, "salt": salt, "hash": digest, "raw": encoded}
    return {"raw": encoded}


class TryHashForm(forms.Form):
    password = forms.CharField(
        label="Type any test password", max_length=64,
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
        help_text="Not stored or logged. Use a made-up value, not a real password.",
    )


@admin_required
def passwords(request):
    users = [{"user": u, "parts": split_hash(u.password)} for u in User.objects.order_by("id")]
    form = TryHashForm(request.POST or None)
    demo = None
    if request.method == "POST" and form.is_valid():
        pw = form.cleaned_data["password"]
        first, second = make_password(pw), make_password(pw)
        demo = {
            "length": len(pw),
            "hashes": [split_hash(first), split_hash(second)],
            "hasher": identify_hasher(first).__class__.__name__,
        }
        form = TryHashForm()  # don't echo the typed value back into the page
    return render(request, "adminpanel/data/passwords.html",
                  {"users": users, "form": form, "demo": demo, **_sidebar()})
