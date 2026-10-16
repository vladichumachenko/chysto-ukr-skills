import unittest

import _path  # noqa: F401
from fetch import FetchError, html_to_markdown, normalize_url, output_name

LONG = "а" * 300


class FetchTest(unittest.TestCase):
    def test_article_body_extracted(self):
        md = html_to_markdown("<html><nav>menu</nav><article><h2>Про хвилю</h2><p>Текст <code>go func()</code>. "
                              + LONG + "</p><pre><code>x := 1</code></pre></article><footer>f</footer></html>")
        self.assertIn("## Про хвилю", md)
        self.assertIn("`go func()`", md)
        self.assertIn("```\nx := 1\n```", md)
        self.assertNotIn("menu", md)
        self.assertNotIn("f\n", md.split("```")[-1])

    def test_falls_back_to_main(self):
        self.assertIn("Тіло", html_to_markdown("<main><p>Тіло " + LONG + "</p></main>"))

    def test_too_little_text_raises(self):
        with self.assertRaises(FetchError):
            html_to_markdown("<html><body><p>коротко</p></body></html>")

    def test_lists_quotes_and_entities(self):
        md = html_to_markdown("<article><ul><li>один</li><li>два &amp; три</li></ul>"
                              "<blockquote><p>цитата</p></blockquote><p>" + LONG + "</p></article>")
        self.assertIn("- один", md)
        self.assertIn("- два & три", md)
        self.assertIn("> цитата", md)

    def test_scripts_and_styles_dropped(self):
        md = html_to_markdown("<article><script>var x=1</script><style>p{}</style><p>" + LONG + "</p></article>")
        self.assertNotIn("var x", md)
        self.assertNotIn("p{}", md)

    def test_aside_inside_article_kept_but_page_chrome_dropped(self):
        md = html_to_markdown("<body><aside>реклама</aside><article><p>" + LONG + "</p>"
                              "<aside><p>Короткий словник хвилі</p></aside></article></body>")
        self.assertIn("Короткий словник хвилі", md)
        self.assertNotIn("реклама", md)

    def test_table_cells_not_glued(self):
        md = html_to_markdown("<article><p>" + LONG + "</p><table><tr><td>задачі</td><td>кладуться</td></tr>"
                              "<tr><td>а</td><td>б</td></tr></table></article>")
        self.assertNotIn("задачікладуться", md)
        self.assertIn("задачі", md)

    def test_nested_list_not_glued(self):
        md = html_to_markdown("<article><p>" + LONG + "</p><ul><li>перший<ul><li>вкладений</li></ul></li></ul></article>")
        self.assertNotIn("першийвкладений", md)
        self.assertIn("вкладений", md)

    def test_normalize_url(self):
        self.assertEqual(normalize_url("chumachenko.net.ua/notes/x"), "https://chumachenko.net.ua/notes/x")
        self.assertEqual(normalize_url("http://a.ua/b"), "http://a.ua/b")
        for bad in ("file:///etc/passwd", "ftp://a.ua/x"):
            with self.assertRaises(FetchError):
                normalize_url(bad)

    def test_output_name(self):
        self.assertEqual(output_name("https://www.chumachenko.net.ua/notes/paddle-out/"), "paddle-out.md")
        self.assertEqual(output_name("https://example.com/"), "example.com.md")


if __name__ == "__main__":
    unittest.main()
