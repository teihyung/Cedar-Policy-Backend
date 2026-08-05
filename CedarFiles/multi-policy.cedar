permit(
  principal == User::"bob",
  action == Action::"viewDocument",
  resource in Folder::"public"
);

permit(
  principal == User::"bob",
  action == Action::"editDocument",
  resource == Document::"report.docx"
);

forbid(
  principal,
  action == Action::"deleteDocument",
  resource
) unless {
  principal in Group::"admins"
};