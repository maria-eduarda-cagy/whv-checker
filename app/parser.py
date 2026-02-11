from bs4 import BeautifulSoup
import re
from typing import Optional, Tuple

SOURCE_URL = "https://immi.homeaffairs.gov.au/what-we-do/whm-program/status-of-country-caps"
TARGET_COUNTRY = "Brazil"


def normalize_status(text: str) -> Optional[str]:
    t = text.strip().lower()
    # Common statuses mapped to canonical values
    if "open" in t:
        return "open"
    if "paused" in t or "pause" in t:
        return "paused"
    if "closed" in t or "close" in t:
        return "closed"
    # Unknown label
    return None


def parse_country_status(html: str, country: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Tabelas com cabeçalhos 'Country' e 'Status'
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            if not rows:
                continue
            header_text = " ".join(cell.get_text(separator=" ", strip=True).lower() for cell in rows[0].find_all(["th", "td"]))
            if "country" in header_text and "status" in header_text:
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if not cells:
                        continue
                    country_cell = cells[0].get_text(separator=" ", strip=True)
                    if re.fullmatch(rf"\s*{re.escape(country)}\s*", country_cell, flags=re.IGNORECASE):
                        status_text = " ".join(c.get_text(separator=" ", strip=True) for c in cells[1:])
                        status = normalize_status(status_text)
                        if status:
                            raw_excerpt = (country_cell + " | " + status_text)[:500]
                            return status, raw_excerpt, None

        return None, None, f"{country} not found or status label missing"
    except Exception as e:
        return None, None, f"Parser error: {e}"


def parse_brazil_status(html: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    return parse_country_status(html, "Brazil")
