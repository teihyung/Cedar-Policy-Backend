permit(
  principal == User::"alice",
  action == Action::"viewDocument",
  resource == Document::"quarterly-report.pdf"
);

forbid(
  principal,
  action == Action::"deleteDocument",
  resource
)
when {
  principal.role != "admin"
};