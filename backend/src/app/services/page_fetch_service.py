from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup


class PageFetchService:
    def fetch_page(self, url: str) -> dict[str, Any]:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(1500)
                final_url = page.url
                html = page.content()
                browser.close()
        except Exception as exc:
            return {
                "status": "error",
                "final_url": url,
                "html": "",
                "markdown": "",
                "error_message": str(exc),
            }

        return {
            "status": "success",
            "final_url": final_url,
            "html": html,
            "markdown": self.html_to_markdown(html),
            "error_message": None,
        }

    @staticmethod
    def html_to_markdown(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        lines: list[str] = []

        for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = node.get_text(" ", strip=True)
            if not text:
                continue
            if node.name == "h1":
                lines.append(f"# {text}")
            elif node.name == "h2":
                lines.append(f"## {text}")
            elif node.name == "h3":
                lines.append(f"### {text}")
            elif node.name == "li":
                lines.append(f"- {text}")
            else:
                lines.append(text)

        return "\n\n".join(lines)
