def static_checks(diff):
    issues = []

    if "async void" in diff:
        issues.append("Avoid async void except for event handlers.")

    if "catch (Exception)" in diff:
        issues.append("Avoid catching generic Exception.")

    if "Console.WriteLine" in diff:
        issues.append("Use ILogger instead of Console.WriteLine.")

    if "DateTime.Now" in diff:
        issues.append("Use DateTime.UtcNow instead.")

    return issues