# NoSQL features (MongoDB) · shot list

Save each screenshot in this folder with the filename shown. Do this folder after `01-sql-postgresql`. Check that bob's account is **Active** again.

- [ ] **`13-transfer-drafts.png`**: Transfer drafts (`transfer_drafts`)
  As `alice`: **Transfer** → to bob, ฿300 → **Save as draft** → **Edit** amount to ฿350 → save.
  Show: the Drafts list with the ฿350 draft.
  Then select **Send now**; the draft disappears from the list. Optionally take a second screenshot of the empty list as `13b-draft-sent.png`.

- [ ] **`14-notifications.png`**: Notifications (`notifications`)
  As `bob`: **Notifications** → **Mark as read** on one → **Dismiss** another.
  Show: the "Money received" item, the read/unread styling and the unread count in the sidebar.

- [ ] **`15-admin-broadcast.png`**: Broadcast (`notifications`, bulk insert)
  As `admin`: **Broadcast** → leave the recipient empty → title "Maintenance Saturday 02:00" → **Send**.
  Show: "Sent to N user(s)." on the notifications list.

- [ ] **`16-support-ticket.png`**: Support ticket (`support_tickets`, embedded messages)
  As `alice`: **Support → New ticket** "Card blocked", Card, High.
  As `admin`: **Support desk** → open it → reply → status **In progress** → **Update status**.
  Show: the thread with the customer message and the staff reply bubble, plus the status chip.

- [ ] **`17-activity-logs.png`**: Activity logs (`activity_logs`)
  As `admin`: **Activity logs** → Result = Failed → **Filter** → **Review** one log → tick Reviewed, add a note → save.
  Show: the filtered list with the "Reviewed" chip and the note.
