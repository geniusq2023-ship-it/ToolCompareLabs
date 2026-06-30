"""Standalone test for _extract_winner_from_html logic."""
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from saas_matrix_engine import _extract_winner_from_html, _determine_winner_from_text

HTML_PATH = os.path.join(SCRIPT_DIR, "..", "src", "content", "html", "omnisend-vs-klaviyo.html")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

print("=" * 60)
print("Testing _extract_winner_from_html")
print("=" * 60)

winner, reason = _extract_winner_from_html(html, "Omnisend", "Klaviyo")
print(f"\nDetected winner : {winner}")
print(f"Verdict reason  : {reason[:200]}...")

print("\n" + "=" * 60)
print("Testing _determine_winner_from_text with raw verdict-box text")
print("=" * 60)

from bs4 import BeautifulSoup
soup = BeautifulSoup(html, "html.parser")
verdict_box = soup.find(class_="verdict-box")
if verdict_box:
    text = verdict_box.get_text(separator=" ", strip=True)
    print(f"\n.verdict-box text:\n{text[:400]}...")
    w, r = _determine_winner_from_text(text, "Omnisend", "Klaviyo")
    print(f"\n--> Winner from _determine_winner_from_text: {w}")
else:
    print("No .verdict-box found!")

print("\n" + "=" * 60)
print("Testing _determine_winner_from_text with last paragraphs")
print("=" * 60)

paragraphs = soup.find_all("p")
for p in reversed(paragraphs[-5:]):
    text = p.get_text(separator=" ", strip=True)
    w, r = _determine_winner_from_text(text, "Omnisend", "Klaviyo")
    if w:
        print(f"\nFound winner in paragraph:\n{text[:300]}...")
        print(f"--> Winner: {w}")
        break
else:
    print("No winner found in last 5 paragraphs.")
