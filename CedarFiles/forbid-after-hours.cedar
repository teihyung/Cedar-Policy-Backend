forbid(
  principal,
  action == Action::"deletePolicy",
  resource
) when {
  context.hour < 9 || context.hour > 17
};