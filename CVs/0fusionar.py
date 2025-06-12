import os
from pypdf import PdfWriter

# Create a merger object
merger = PdfWriter()

# Define the target directory
pdf_dir = r'C:/repositories/profes/CVs'


pdf_files = sorted([
    f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')
])

# Append each PDF
for pdf in pdf_files:
    pdf_path = os.path.join(pdf_dir, pdf)
    print(f"Merging: {pdf_path}")
    merger.append(pdf_path)

# Output file
output_path = os.path.join(pdf_dir, 'CVs/HojasDeVida.pdf')
merger.write(output_path)
merger.close()

print(f"\nAll PDFs merged into: {output_path}")