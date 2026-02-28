from core.static_analyzer import static_checks

def test_async_void():
    diff = "async void Test() {}"
    issues = static_checks(diff)
    assert "Avoid async void" in issues[0]