import re
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm
from PIL import Image, ImageDraw, ImageFont

def wrap_item_text_pdf(text: str, font: str, size: float, max_w: float) -> list[str]:
    """Wrap item_desc into at most 2 lines, ensuring (x/y) counter is never cut off."""
    if stringWidth(text, font, size) <= max_w:
        return [text]

    # Extract counter suffix like ' (1/2)' if present
    match = re.search(r'\s+(\(\d+/\d+\))$', text)
    suffix = match.group(1) if match else ''

    words = text.split()
    if not words:
        return [text]

    # Try word-wrapping across 2 lines
    l1_words = []
    l2_words = []

    # Fill line 1
    for i, word in enumerate(words):
        cand = ' '.join(l1_words + [word])
        if stringWidth(cand, font, size) <= max_w:
            l1_words.append(word)
        else:
            l2_words = words[i:]
            break

    # If no word fit in line 1 (single huge word)
    if not l1_words and l2_words:
        first_word = l2_words[0]
        chars = ''
        for ch in first_word:
            if stringWidth(chars + ch, font, size) <= max_w:
                chars += ch
            else:
                break
        l1_words = [chars] if chars else [first_word[:1]]
        rem_first = first_word[len(chars):]
        l2_words = ([rem_first] if rem_first else []) + l2_words[1:]

    line1 = ' '.join(l1_words)
    line2 = ' '.join(l2_words)

    # Check if line2 fits
    if stringWidth(line2, font, size) <= max_w:
        return [line1, line2]

    # If line2 exceeds max_w, truncate line2 while preserving counter suffix
    if suffix:
        if line2.endswith(suffix):
            stem = line2[:-len(suffix)].rstrip()
        else:
            stem = line2.rstrip()
        while stem:
            cand = stem + '… ' + suffix
            if stringWidth(cand, font, size) <= max_w:
                return [line1, cand]
            stem = stem[:-1]
        return [line1, '… ' + suffix]
    else:
        while line2:
            cand = line2 + '…'
            if stringWidth(cand, font, size) <= max_w:
                return [line1, cand]
            line2 = line2[:-1]
        return [line1, '…']


def wrap_item_text_image(draw, text: str, font, max_w: int) -> list[str]:
    """Wrap item_desc into at most 2 lines in PIL image, ensuring (x/y) counter is never cut off."""
    bbox = draw.textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] <= max_w:
        return [text]

    # Extract counter suffix like ' (1/2)' if present
    match = re.search(r'\s+(\(\d+/\d+\))$', text)
    suffix = match.group(1) if match else ''

    words = text.split()
    if not words:
        return [text]

    l1_words = []
    l2_words = []

    for i, word in enumerate(words):
        cand = ' '.join(l1_words + [word])
        bbox = draw.textbbox((0, 0), cand, font=font)
        if bbox[2] - bbox[0] <= max_w:
            l1_words.append(word)
        else:
            l2_words = words[i:]
            break

    if not l1_words and l2_words:
        first_word = l2_words[0]
        chars = ''
        for ch in first_word:
            bbox = draw.textbbox((0, 0), chars + ch, font=font)
            if bbox[2] - bbox[0] <= max_w:
                chars += ch
            else:
                break
        l1_words = [chars] if chars else [first_word[:1]]
        rem_first = first_word[len(chars):]
        l2_words = ([rem_first] if rem_first else []) + l2_words[1:]

    line1 = ' '.join(l1_words)
    line2 = ' '.join(l2_words)

    bbox2 = draw.textbbox((0, 0), line2, font=font)
    if bbox2[2] - bbox2[0] <= max_w:
        return [line1, line2]

    if suffix:
        if line2.endswith(suffix):
            stem = line2[:-len(suffix)].rstrip()
        else:
            stem = line2.rstrip()
        while stem:
            cand = stem + '… ' + suffix
            bbox_c = draw.textbbox((0, 0), cand, font=font)
            if bbox_c[2] - bbox_c[0] <= max_w:
                return [line1, cand]
            stem = stem[:-1]
        return [line1, '… ' + suffix]
    else:
        while line2:
            cand = line2 + '…'
            bbox_c = draw.textbbox((0, 0), cand, font=font)
            if bbox_c[2] - bbox_c[0] <= max_w:
                return [line1, cand]
            line2 = line2[:-1]
        return [line1, '…']


if __name__ == '__main__':
    PAGE_W = 43.8 * mm
    MARGIN = 3 * mm
    USABLE = PAGE_W - 2 * MARGIN

    test_cases = [
        'Shirt',
        'Shirt (1/2)',
        'BABY BED PREMIUM',
        'BABY BED PREMIUM (1/2)',
        'Gentleman Formal 3-Piece Tuxedo Suit with Waistcoat (1/2)',
        'Heavy Embroidered Bridal Lehenga with Dupatta and Blouse Piece (1/2)',
        'SUPERLONGITEMNAMEWITHOUTANYSPACES (1/2)',
        'SUPERLONGITEMNAMEWITHOUTANYSPACES',
    ]

    print('=== PDF WRAP TESTS ===')
    for t in test_cases:
        lines = wrap_item_text_pdf(t, 'Helvetica-Bold', 10, USABLE)
        print(f'{t}')
        for idx, l in enumerate(lines):
            w = stringWidth(l, 'Helvetica-Bold', 10)
            print(f'  L{idx+1} ({w:.1f}/{USABLE:.1f} pt): "{l}"')

    print('\n=== PIL IMAGE WRAP TESTS (35x40mm) ===')
    img = Image.new('RGB', (413, 472))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype('arialbd.ttf', 34)
    max_w = 413 - 60

    for t in test_cases:
        lines = wrap_item_text_image(draw, t, font, max_w)
        print(f'{t}')
        for idx, l in enumerate(lines):
            bbox = draw.textbbox((0, 0), l, font=font)
            w = bbox[2] - bbox[0]
            print(f'  L{idx+1} ({w}/{max_w} px): "{l}"')
