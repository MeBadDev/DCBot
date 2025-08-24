

import cloudscraper

DOWNLOAD_LINK_TEST = "https://www.curseforge.com/minecraft/worlds/mineparty/download/6881651"

def test_download():
	scraper = cloudscraper.create_scraper(
		interpreter='js2py',
		debug=True,
	)
	response = scraper.get(DOWNLOAD_LINK_TEST, stream=True)
	print(f"Status: {response.status_code}")
	print(f"Headers: {dict(response.headers)}")
	print(f"Content-Type: {response.headers.get('Content-Type')}")
	content = response.content
	print(f"First 500 bytes: {content[:500]!r}")
	if response.status_code == 200:
		with open('test_download.zip', 'wb') as f:
			f.write(content)
		print("Downloaded to test_download.zip")
	else:
		print("Download failed.")

if __name__ == "__main__":
	test_download()

