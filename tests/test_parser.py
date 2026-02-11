from app.parser import parse_brazil_status


def test_parse_brazil_status_table():
    html = """
    <html>
    <body>
      <table>
        <tr><th>Country</th><th>Status</th></tr>
        <tr><td>Argentina</td><td>closed</td></tr>
        <tr><td>Brazil</td><td>open</td></tr>
        <tr><td>Chile</td><td>paused</td></tr>
      </table>
    </body>
    </html>
    """
    status, raw, err = parse_brazil_status(html)
    assert err is None
    assert status == "open"
    assert "Brazil" in raw
