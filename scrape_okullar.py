"""Scrape schools from meb.gov.tr school directory and write JSON."""

import argparse
import json
import sys
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.parse import urlencode

ENDPOINT = "https://www.meb.gov.tr/baglantilar/okullar/okullar_ajax.php"
PAGE_SIZE = 500


def fetch_page(il: int, ilce: int, start: int, length: int) -> dict[str, Any]:
    payload = {
        "draw": 1,
        "start": start,
        "length": length,
        "search[value]": "",
        "search[regex]": "false",
        "il": il,
        "ilce": ilce,
        "order[0][column]": 0,
        "order[0][dir]": "asc",
        "columns[0][data]": "OKUL_ADI",
        "columns[0][searchable]": "true",
        "columns[0][orderable]": "true",
        "columns[0][search][value]": "",
        "columns[0][search][regex]": "false",
    }
    data = urlencode(payload).encode("utf-8")
    req = Request(
        ENDPOINT,
        data=data,
        headers={
            "accept": "application/json, text/javascript, */*; q=0.01",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://www.meb.gov.tr",
            "referer": f"https://www.meb.gov.tr/baglantilar/okullar/index.php?ILKODU={il}&ILCEKODU={ilce}",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            "x-requested-with": "XMLHttpRequest",
        },
        method="POST",
    )
    with urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_row(row: dict[str, str]) -> dict[str, str]:
    raw_name: str = row.get("OKUL_ADI", "")
    parts = [p.strip() for p in raw_name.split(" - ", 2)]
    province = parts[0] if len(parts) > 0 else ""
    district = parts[1] if len(parts) > 1 else ""
    school_name = parts[2] if len(parts) > 2 else raw_name

    yol = row.get("YOL", "")
    yol_parts = yol.split("/")
    province_code = yol_parts[0] if len(yol_parts) > 0 else ""
    district_code = yol_parts[1] if len(yol_parts) > 1 else ""
    institution_code = yol_parts[2] if len(yol_parts) > 2 else ""

    host = row.get("HOST", "")
    website = f"http://{host}.meb.k12.tr" if host else ""

    return {
        "province": province,
        "district": district,
        "schoolName": school_name,
        "provinceCode": province_code,
        "districtCode": district_code,
        "institutionCode": institution_code,
        "host": host,
        "website": website,
    }


def scrape(il: int, ilce: int, delay: float) -> list[dict[str, str]]:
    first = fetch_page(il, ilce, 0, PAGE_SIZE)
    total = int(first.get("recordsTotal", 0))
    print(f"il={il} ilce={ilce}: {total} schools", file=sys.stderr)

    rows = list(first.get("data", []))
    while len(rows) < total:
        if delay:
            time.sleep(delay)
        page = fetch_page(il, ilce, len(rows), PAGE_SIZE)
        chunk = page.get("data", [])
        if not chunk:
            break
        rows.extend(chunk)
        print(f"  fetched {len(rows)}/{total}", file=sys.stderr)

    return [parse_row(r) for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--il", type=int, default=42, help="province code (e.g. 42=Konya, 0=all)")
    ap.add_argument("--ilce", type=int, default=0, help="district code (0=all)")
    ap.add_argument("--delay", type=float, default=0.3, help="seconds between page requests")
    ap.add_argument("-o", "--output", default="okullar.json", help="output JSON file")
    args = ap.parse_args()

    schools = scrape(args.il, args.ilce, args.delay)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(schools, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(schools)} schools to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
