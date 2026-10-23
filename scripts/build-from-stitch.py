#!/usr/bin/env python3
"""Transform Stitch-exported HTML into a production landing page."""

from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/tmp/lp-painting.html")
MAP_PATH = ROOT / "image-map.json"


def add_heading_ids(html: str) -> str:
    mapping_h = {
        "Our Certified Painting & Pressure Washing Services": "services",
        "We Don't Just Apply Paint.We Restore & Elevate Value.": "our-work",
        "Built On Three Unbreakable Principles": "why-us",
        "Serving Washington & Oregon": "service-areas",
        "What Our Clients Say": "reviews",
        "Interactive Cost Estimator": "cost-calculator",
        "Request Free In-Home Estimate": "estimate",
        "Let's Bring Your Vision To Life. Contact LP Painting Today.": "contact",
    }

    def repl(m: re.Match[str]) -> str:
        attrs, content = m.group(1), m.group(2)
        plain = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", content))).strip()
        plain_n = plain.replace("’", "'")
        sid = None
        for key, value in mapping_h.items():
            kn = key.replace("’", "'")
            if kn in plain_n or plain_n.startswith(kn[:28]):
                sid = value
                break
        if not sid or "id=" in attrs:
            return m.group(0)
        return f'<h2{attrs} id="{sid}" style="scroll-margin-top:6rem">{content}</h2>'

    return re.sub(r"<h2([^>]*)>(.*?)</h2>", repl, html, flags=re.S | re.I)


def fix_nav(html: str) -> str:
    for text, href in [
        ("Services", "#services"),
        ("Why Us", "#why-us"),
        ("Our Work", "#our-work"),
        ("Reviews", "#reviews"),
        ("Service Areas", "#service-areas"),
        ("Get a Free Estimate", "#estimate"),
        ("Request an Estimate", "#estimate"),
        ("Calculate Ballpark", "#cost-calculator"),
        ("Interior Painting", "#services"),
        ("Exterior Painting", "#services"),
        ("Pressure Washing", "#services"),
        ("Commercial Painting", "#services"),
    ]:
        html = re.sub(
            rf'(<a\b[^>]*\bhref=")#[^"]*("[^>]*>\s*{re.escape(text)}\s*</a>)',
            rf"\1{href}\2",
            html,
            flags=re.I,
        )
    return html


def dedupe_material_links(html: str) -> str:
    seen = False

    def repl(m: re.Match[str]) -> str:
        nonlocal seen
        if seen:
            return ""
        seen = True
        return m.group(0)

    return re.sub(r"<link[^>]+Material\+Symbols[^>]*>", repl, html)


EXTRA_JS = r"""
<script>
document.addEventListener('DOMContentLoaded', () => {
  if (typeof updateCalculator === 'function') updateCalculator();
  const slider = document.getElementById('sqftSlider');
  if (slider) slider.addEventListener('input', updateCalculator);

  const form = document.getElementById('leadQuoteForm');
  const modal = document.getElementById('formSuccessModal');
  if (form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const lines = [];
      form.querySelectorAll('input, select, textarea').forEach((el) => {
        const val = (el.value || '').trim();
        if (!val) return;
        const label = el.name || el.placeholder || el.getAttribute('aria-label') || el.type || 'field';
        lines.push(label + ': ' + val);
      });
      const subject = encodeURIComponent('Free Estimate Request — LP Painting');
      const body = encodeURIComponent(lines.join('\n') || 'New estimate request from website');
      if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }
      window.location.href = 'mailto:LPpainting2903@gmail.com?subject=' + subject + '&body=' + body;
    });
  }

  const closeModal = () => {
    if (!modal) return;
    modal.classList.add('hidden');
    modal.classList.remove('flex');
  };
  document.querySelectorAll('[data-close-modal]').forEach((btn) => btn.addEventListener('click', closeModal));
  if (modal) {
    modal.querySelectorAll('button').forEach((btn) => btn.addEventListener('click', closeModal));
  }

  document.querySelectorAll('a[href^="#"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href').slice(1);
      if (!id) return;
      const el = document.getElementById(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
});
</script>
"""


def main() -> None:
    html = SOURCE.read_text()
    mapping = json.loads(MAP_PATH.read_text())

    # Prefer higher-quality Stitch screen assets for home photography
    for url, local in list(mapping.items()):
        if local == "/images/photo-1.jpg":
            mapping[url] = "/images/hero-exterior.jpg"
        elif local == "/images/photo-2.jpg":
            mapping[url] = "/images/portfolio-0239.jpg"

    for url, local in mapping.items():
        html = html.replace(url, local)

    html = html.replace('<meta content="web_standard" name="shell-type">', "")
    html = re.sub(r'<html([^>]*)\sstyle=""', r"<html\1", html)
    title = "<title>LP Painting | Interior &amp; Exterior Painting in WA &amp; OR</title>"
    if re.search(r"<title>.*?</title>", html, flags=re.I | re.S):
        html = re.sub(r"<title>.*?</title>", title, html, count=1, flags=re.I | re.S)
    else:
        html = html.replace("<head>", f"<head>{title}", 1)

    seo = """
<meta name="description" content="LP Painting — professional interior & exterior painting and pressure washing across Washington & Oregon. Call (360) 326-5768 for a free estimate.">
<meta name="theme-color" content="#005ea4">
<link rel="icon" type="image/jpeg" href="/images/logo.jpg">
"""
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">' + seo, 1)

    html = add_heading_ids(html)
    html = fix_nav(html)
    html = dedupe_material_links(html)

    if "</body>" in html:
        html = html.replace("</body>", EXTRA_JS + "</body>", 1)
    else:
        html += EXTRA_JS

    out = ROOT / "index.html"
    out.write_text(html)
    print(f"Wrote {out} ({len(html)} bytes)")

    rem = re.findall(r"https://lh3\.googleusercontent\.com[^\"')\s]+", html)
    print(f"Remaining remote image URLs: {len(rem)}")


if __name__ == "__main__":
    main()
