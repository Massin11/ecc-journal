import sys
sys.path.insert(0, 'scripts')
import xml.etree.ElementTree as ET
from ecc_journal import ATOM_NS, ARXIV_NS

# Realistic sample of arXiv's actual Atom API response format
MOCK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2608.02773v1</id>
    <published>2026-08-03T18:13:57Z</published>
    <title>Quantum error correction at ultra-low overhead</title>
    <summary>Suppressing errors is the central challenge for useful large-scale
quantum computing. We introduce Cornucopia codes, a family of practical,
hardware-efficient quantum LDPC codes. Code available at
https://github.com/example-lab/cornucopia-codes for reproducing all results.</summary>
    <author><name>Zhide Lu</name></author>
    <author><name>Weikang Li</name></author>
    <author><name>Dong-Ling Deng</name></author>
    <arxiv:comment>15 pages, 6 figures. Code: https://github.com/example-lab/cornucopia-codes</arxiv:comment>
    <link title="pdf" href="http://arxiv.org/pdf/2608.02773v1" rel="related" type="application/pdf"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2608.23460v1</id>
    <published>2026-08-25T10:00:00Z</published>
    <title>Satisfying Quantum Codes: Physics-Informed and Hardware-Aware Code Design with SAT Solvers</title>
    <summary>We present a framework for designing quantum error correcting codes
using SAT solvers, incorporating physical hardware constraints directly
into the search.</summary>
    <author><name>Ben DalFavero</name></author>
    <author><name>Ryan LaRose</name></author>
    <arxiv:comment>12 pages</arxiv:comment>
    <link title="pdf" href="http://arxiv.org/pdf/2608.23460v1" rel="related" type="application/pdf"/>
  </entry>
</feed>"""

root = ET.fromstring(MOCK_XML)
papers = []
for entry in root.findall(f"{ATOM_NS}entry"):
    arxiv_id_full = entry.find(f"{ATOM_NS}id").text.strip()
    arxiv_id = arxiv_id_full.rsplit("/", 1)[-1]
    title = entry.find(f"{ATOM_NS}title").text.strip().replace("\n", " ")
    summary = entry.find(f"{ATOM_NS}summary").text.strip().replace("\n", " ")
    authors = [a.find(f"{ATOM_NS}name").text for a in entry.findall(f"{ATOM_NS}author")]
    comment_el = entry.find(f"{ARXIV_NS}comment")
    comment = comment_el.text.strip() if comment_el is not None and comment_el.text else ""
    published = entry.find(f"{ATOM_NS}published").text[:10]
    papers.append(dict(arxiv_id=arxiv_id, title=title, summary=summary,
                        authors=authors, comment=comment, published=published))

for p in papers:
    print(p['arxiv_id'], '|', p['title'])
    print('  authors:', p['authors'])
    print('  published:', p['published'])
    print('  comment:', p['comment'])
    print()

assert papers[0]['arxiv_id'] == '2608.02773v1'
assert papers[0]['authors'] == ['Zhide Lu', 'Weikang Li', 'Dong-Ling Deng']
assert papers[0]['published'] == '2026-08-03'
assert 'github.com' in papers[0]['comment']
print("All XML parsing assertions passed.")
