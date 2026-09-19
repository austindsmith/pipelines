from playwright.sync_api import sync_playwright


def open_browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chromium", headless=False)
        page = browser.new_page()
        page.goto("https://google.com")
        print(page.title())
        page.pause()
        browser.close()


def main():
    open_browser()


if __name__ == "__main__":
    main()
