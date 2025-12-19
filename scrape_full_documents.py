"""
Full Document Scraper - Downloads COMPLETE unfiltered content
Scrapes entire text from the provided URLs without any summarization.
"""

import requests
from bs4 import BeautifulSoup
from pathlib import Path
import time
import PyPDF2
from io import BytesIO

class FullDocumentScraper:
    def __init__(self, output_dir="data/pdfs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
    
    def extract_text_from_pdf(self, pdf_content):
        """Extract all text from PDF content."""
        try:
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            full_text = []
            total_pages = len(pdf_reader.pages)
            
            print(f"    Extracting text from {total_pages} pages...")
            
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()
                full_text.append(text)
                
                if (page_num + 1) % 10 == 0:
                    print(f"    Processed {page_num + 1}/{total_pages} pages...")
            
            return '\n\n'.join(full_text)
        
        except Exception as e:
            print(f"    ❌ PDF extraction error: {str(e)}")
            return None
    
    def scrape_html_content(self, url, ticker, doc_name):
        """Scrape complete HTML content without filtering."""
        print(f"\n{'='*70}")
        print(f"Scraping: {ticker} - {doc_name}")
        print(f"{'='*70}")
        print(f"URL: {url}")
        
        try:
            print("  Fetching page...")
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            print("  Parsing HTML...")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove only scripts, styles, and ads - keep ALL content
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()
            
            # Get ALL text content
            full_text = soup.get_text(separator='\n', strip=False)
            
            # Minimal cleaning - just normalize line breaks
            lines = [line.rstrip() for line in full_text.split('\n')]
            full_text = '\n'.join(line for line in lines if line or lines[lines.index(line)-1:lines.index(line)])
            
            # Save complete content
            output_file = self.output_dir / f"{ticker}_{doc_name}_FULL.txt"
            with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(full_text)
            
            char_count = len(full_text)
            word_count = len(full_text.split())
            
            print(f"  ✓ Scraped successfully!")
            print(f"  ✓ Characters: {char_count:,}")
            print(f"  ✓ Words: {word_count:,}")
            print(f"  ✓ Saved to: {output_file.name}")
            
            return output_file
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return None
    
    def download_pdf_content(self, url, ticker, doc_name):
        """Download and extract complete PDF content."""
        print(f"\n{'='*70}")
        print(f"Downloading PDF: {ticker} - {doc_name}")
        print(f"{'='*70}")
        print(f"URL: {url}")
        
        try:
            print("  Downloading PDF...")
            response = requests.get(url, headers=self.headers, timeout=60)
            response.raise_for_status()
            
            print("  Extracting text from PDF...")
            full_text = self.extract_text_from_pdf(response.content)
            
            if not full_text:
                print("  ⚠ Could not extract text, saving as PDF file")
                output_file = self.output_dir / f"{ticker}_{doc_name}_FULL.pdf"
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                print(f"  ✓ Saved PDF: {output_file.name}")
                return output_file
            
            # Save extracted text
            output_file = self.output_dir / f"{ticker}_{doc_name}_FULL.txt"
            with open(output_file, 'w', encoding='utf-8', errors='ignore') as f:
                f.write(full_text)
            
            char_count = len(full_text)
            word_count = len(full_text.split())
            
            print(f"  ✓ Extracted successfully!")
            print(f"  ✓ Characters: {char_count:,}")
            print(f"  ✓ Words: {word_count:,}")
            print(f"  ✓ Saved to: {output_file.name}")
            
            return output_file
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            return None


def main():
    print("=" * 70)
    print("FULL DOCUMENT SCRAPER")
    print("Downloads COMPLETE, UNFILTERED content for RAG system")
    print("=" * 70)
    
    scraper = FullDocumentScraper()
    
    # Document sources with full URLs
    documents = [
        {
            'ticker': 'AAPL',
            'name': 'Q4_2023_Earnings_Transcript',
            'url': 'https://www.moomoo.com/news/post/29297668/apple-q4-2023-earnings-call-transcript?level=3&data_ticket=1766037594253011',
            'type': 'html'
        },
        {
            'ticker': 'MSFT',
            'name': 'Q4_2023_Earnings_Transcript',
            'url': 'https://www.fool.com/earnings/call-transcripts/2023/07/25/microsoft-msft-q4-2023-earnings-call-transcript/',
            'type': 'html'
        },
        {
            'ticker': 'NVDA',
            'name': 'Q4_FY24_10K',
            'url': 'https://s201.q4cdn.com/141608511/files/doc_financials/2024/q4/1cbe8fe7-e08a-46e3-8dcc-b429fc06c1a4.pdf',
            'type': 'pdf'
        },
        {
            'ticker': 'GOOGL',
            'name': 'Q4_2023_10K',
            'url': 'https://s206.q4cdn.com/479360582/files/doc_financials/2023/q4/goog-10-k-2023-final.pdf',
            'type': 'pdf'
        },
        {
            'ticker': 'META',
            'name': 'Q4_2023_Earnings_Transcript',
            'url': 'https://s21.q4cdn.com/399680738/files/doc_financials/2023/q4/META-Q4-2023-Earnings-Call-Transcript.pdf',
            'type': 'pdf'
        }
    ]
    
    results = []
    
    print("\n🚀 Starting full document download...")
    print("⚠️  This will download COMPLETE documents without filtering")
    print("⏱️  This may take several minutes...\n")
    
    for doc in documents:
        if doc['type'] == 'html':
            result = scraper.scrape_html_content(
                url=doc['url'],
                ticker=doc['ticker'],
                doc_name=doc['name']
            )
        else:  # pdf
            result = scraper.download_pdf_content(
                url=doc['url'],
                ticker=doc['ticker'],
                doc_name=doc['name']
            )
        
        results.append({
            'ticker': doc['ticker'],
            'name': doc['name'],
            'success': result is not None,
            'file': result
        })
        
        # Be respectful - delay between requests
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print(f"\n✓ Successfully downloaded: {successful}/{total} documents\n")
    
    if successful > 0:
        print("Downloaded files:")
        for r in results:
            status = "✓" if r['success'] else "❌"
            file_name = r['file'].name if r['file'] else "Failed"
            print(f"  {status} {r['ticker']}: {file_name}")
    
    if successful < total:
        print("\n⚠️  Some documents failed to download.")
        print("   You may need to download them manually.")
    
    print("\n" + "=" * 70)
    print("✓ All documents contain COMPLETE, UNFILTERED content")
    print("✓ Ready for RAG vector database ingestion")
    print("=" * 70)


if __name__ == "__main__":
    main()
