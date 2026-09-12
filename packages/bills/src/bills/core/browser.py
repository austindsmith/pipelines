from playwright.sync_api import sync_playwright



def open_browser():
    with sync_playwright() as p:
     browser = p.chromium.launch()
     page = browser.new_page()


def main():
    open_browser()


if __name__ == 'main':
    main()
