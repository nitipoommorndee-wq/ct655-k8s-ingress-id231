import sys, pypdfium2 as pdfium
from PIL import Image
for name in sys.argv[1:]:
    pdf = pdfium.PdfDocument(name + ".pdf"); n = len(pdf); print(name, n, "pages")
    ims = [pdf[i].render(scale=0.9).to_pil() for i in range(n)]
    for k in range(0, n, 6):
        grp = ims[k:k + 6]; w, h = grp[0].size
        sheet = Image.new("RGB", (w * 3, h * ((len(grp) + 2) // 3)), "#888")
        for j, im in enumerate(grp): sheet.paste(im, ((j % 3) * w + 0, (j // 3) * h))
        sheet.save(f".pages-{name}-{k // 6}.png")
