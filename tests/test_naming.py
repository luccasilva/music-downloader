from music_downloader.naming import sanitize_filename, OUTPUT_TEMPLATE


def test_replaces_windows_invalid_chars():
    assert sanitize_filename('a/b:c*d?e"f<g>h|i\\j') == "a_b_c_d_e_f_g_h_i_j"


def test_collapses_whitespace_and_trims():
    assert sanitize_filename("  hello   world  ") == "hello world"


def test_strips_trailing_dots():
    assert sanitize_filename("name...") == "name"


def test_empty_becomes_untitled():
    assert sanitize_filename("   ") == "untitled"


def test_output_template_uses_artist_title_with_uploader_fallback():
    assert OUTPUT_TEMPLATE == "%(artist,uploader)s - %(title)s.%(ext)s"
