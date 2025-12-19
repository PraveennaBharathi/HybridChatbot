"""
Document Preprocessing Pipeline for Financial Documents
Implements intelligent cleaning, normalization, and chunking for RAG quality.

Pipeline:
1. Text Cleaning (remove noise, boilerplate)
2. Financial Text Normalization (currencies, dates, numbers)
3. Semantic Chunking (by sections, speakers, Q&A)
4. Metadata Enrichment (company, date, document type, section)
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
import json


class FinancialDocumentPreprocessor:
    """Preprocesses financial documents (earnings transcripts, 10-Ks) for RAG."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        # Patterns for cleaning
        self.noise_patterns = [
            r'©\s*\d{4}.*?(?:\n|$)',  # Copyright
            r'Terms\s*\|\s*Privacy',  # Legal boilerplate
            r'Page\s+\d+\s+of\s+\d+',  # Page numbers
            r'Table\s+of\s+Contents',  # TOC headers
            r'^\s*\d+\s*$',  # Standalone page numbers
            r'https?://[^\s]+',  # URLs (keep domain context)
        ]
        
        # Currency normalization
        self.currency_map = {
            r'\$': 'USD ',
            r'€': 'EUR ',
            r'£': 'GBP ',
            r'¥': 'JPY ',
            r'S\$': 'SGD ',
        }
        
        # Company metadata
        self.company_info = {
            'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'},
            'MSFT': {'name': 'Microsoft Corp', 'sector': 'Technology'},
            'NVDA': {'name': 'NVIDIA Corp', 'sector': 'Technology'},
            'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Technology'},
            'META': {'name': 'Meta Platforms', 'sector': 'Technology'},
        }
    
    def clean_text(self, text: str) -> str:
        """Remove noise and boilerplate."""
        cleaned = text
        
        # Remove noise patterns
        for pattern in self.noise_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r' {2,}', ' ', cleaned)
        
        # Remove navigation/menu artifacts (common in scraped HTML)
        nav_keywords = ['Skip to content', 'Main menu', 'Search for:', 'Subscribe', 
                       'Sign in', 'Sign up', 'Cookie Policy', 'Privacy Policy']
        for keyword in nav_keywords:
            cleaned = cleaned.replace(keyword, '')
        
        return cleaned.strip()
    
    def normalize_financial_text(self, text: str) -> str:
        """Normalize financial entities for better semantic matching."""
        normalized = text
        
        # Normalize currency symbols to ISO codes
        for symbol, code in self.currency_map.items():
            normalized = re.sub(symbol, code, normalized)
        
        # Normalize large numbers with context
        # $10.5B → USD 10.5 billion
        normalized = re.sub(
            r'USD\s*(\d+\.?\d*)\s*([BbMmKk])\b',
            lambda m: f"USD {m.group(1)} {self._expand_magnitude(m.group(2))}",
            normalized
        )
        
        # Normalize percentages (keep as is but ensure space)
        normalized = re.sub(r'(\d+\.?\d*)%', r'\1 percent', normalized)
        
        # Normalize dates to more consistent format (but keep original for context)
        # This is light normalization - we keep original dates for readability
        
        return normalized
    
    def _expand_magnitude(self, magnitude: str) -> str:
        """Expand B/M/K to full words."""
        mapping = {
            'B': 'billion', 'b': 'billion',
            'M': 'million', 'm': 'million',
            'K': 'thousand', 'k': 'thousand'
        }
        return mapping.get(magnitude, magnitude)
    
    def detect_document_type(self, text: str, filename: str) -> str:
        """Detect if document is earnings transcript or 10-K."""
        if '10-K' in filename or '10K' in filename:
            return '10-K'
        elif 'transcript' in filename.lower() or 'earnings call' in text[:1000].lower():
            return 'earnings_transcript'
        else:
            return 'financial_document'
    
    def extract_metadata_from_filename(self, filename: str) -> Dict:
        """Extract company ticker and date from filename."""
        metadata = {}
        
        # Extract ticker
        for ticker in self.company_info.keys():
            if ticker in filename:
                metadata['ticker'] = ticker
                metadata['company_name'] = self.company_info[ticker]['name']
                metadata['sector'] = self.company_info[ticker]['sector']
                break
        
        # Extract year/quarter
        year_match = re.search(r'20\d{2}', filename)
        if year_match:
            metadata['year'] = year_match.group(0)
        
        quarter_match = re.search(r'Q([1-4])', filename, re.IGNORECASE)
        if quarter_match:
            metadata['quarter'] = f"Q{quarter_match.group(1)}"
        
        return metadata
    
    def chunk_by_sections(self, text: str, doc_type: str) -> List[Tuple[str, Dict]]:
        """Intelligent semantic chunking based on document type."""
        if doc_type == 'earnings_transcript':
            return self._chunk_transcript(text)
        elif doc_type == '10-K':
            return self._chunk_10k(text)
        else:
            return self._chunk_generic(text)
    
    def _chunk_transcript(self, text: str) -> List[Tuple[str, Dict]]:
        """Chunk earnings transcript by speaker turns and sections."""
        chunks = []
        
        # Try to identify sections
        sections = self._identify_transcript_sections(text)
        
        if sections:
            # Chunk by sections
            for section_name, section_text in sections:
                # Further chunk by speaker if possible
                speaker_chunks = self._chunk_by_speaker(section_text)
                
                for speaker, content in speaker_chunks:
                    if len(content.strip()) > 100:  # Minimum chunk size
                        metadata = {
                            'section': section_name,
                            'speaker': speaker,
                            'chunk_type': 'speaker_turn'
                        }
                        chunks.append((content.strip(), metadata))
        else:
            # Fallback: chunk by paragraphs with overlap
            chunks = self._chunk_with_overlap(text, chunk_size=500, overlap=100)
        
        return chunks
    
    def _identify_transcript_sections(self, text: str) -> List[Tuple[str, str]]:
        """Identify major sections in transcript."""
        sections = []
        
        # Common section headers
        section_patterns = [
            (r'(?:^|\n)(Prepared Remarks?|Opening Remarks?)(?:\n|:)', 'Prepared Remarks'),
            (r'(?:^|\n)(Financial Results?|Results?)(?:\n|:)', 'Financial Results'),
            (r'(?:^|\n)(Q&A|Question and Answer|Questions? and Answers?)(?:\n|:)', 'Q&A'),
            (r'(?:^|\n)(Forward[- ]Looking Statements?)(?:\n|:)', 'Forward-Looking Statements'),
            (r'(?:^|\n)(Guidance|Outlook)(?:\n|:)', 'Guidance'),
        ]
        
        # Find section boundaries
        boundaries = []
        for pattern, name in section_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                boundaries.append((match.start(), name))
        
        if not boundaries:
            return []
        
        # Sort by position
        boundaries.sort()
        
        # Extract sections
        for i, (start, name) in enumerate(boundaries):
            end = boundaries[i + 1][0] if i + 1 < len(boundaries) else len(text)
            section_text = text[start:end]
            sections.append((name, section_text))
        
        return sections
    
    def _chunk_by_speaker(self, text: str) -> List[Tuple[str, str]]:
        """Extract speaker turns from transcript."""
        chunks = []
        
        # Pattern for speaker identification
        # Matches: "John Doe, CFO:", "Analyst:", "Operator:", etc.
        speaker_pattern = r'(?:^|\n)([A-Z][a-zA-Z\s\.]+(?:,\s*[A-Z][A-Za-z\s]+)?)\s*[:\-]'
        
        matches = list(re.finditer(speaker_pattern, text, re.MULTILINE))
        
        if matches:
            for i, match in enumerate(matches):
                speaker = match.group(1).strip()
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                
                if content:
                    chunks.append((speaker, content))
        else:
            # No speakers found, return as single chunk
            chunks.append(('Unknown', text))
        
        return chunks
    
    def _chunk_10k(self, text: str) -> List[Tuple[str, Dict]]:
        """Chunk 10-K by items and sections."""
        chunks = []
        
        # Identify 10-K items
        item_pattern = r'(?:^|\n)(Item\s+\d+[A-Z]?\.?\s+[^\n]+)'
        matches = list(re.finditer(item_pattern, text, re.IGNORECASE | re.MULTILINE))
        
        if matches:
            for i, match in enumerate(matches):
                item_name = match.group(1).strip()
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                section_text = text[start:end]
                
                # Further chunk large sections
                if len(section_text) > 2000:
                    sub_chunks = self._chunk_with_overlap(section_text, chunk_size=600, overlap=100)
                    for j, (chunk_text, _) in enumerate(sub_chunks):
                        metadata = {
                            'section': item_name,
                            'subsection': f"{item_name}_part_{j+1}",
                            'chunk_type': '10k_section'
                        }
                        chunks.append((chunk_text, metadata))
                else:
                    metadata = {
                        'section': item_name,
                        'chunk_type': '10k_section'
                    }
                    chunks.append((section_text.strip(), metadata))
        else:
            # Fallback to generic chunking
            chunks = self._chunk_with_overlap(text, chunk_size=600, overlap=100)
        
        return chunks
    
    def _chunk_generic(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[Tuple[str, Dict]]:
        """Generic chunking with overlap."""
        return self._chunk_with_overlap(text, chunk_size, overlap)
    
    def _chunk_with_overlap(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[Tuple[str, Dict]]:
        """Chunk text with overlap for context preservation."""
        words = text.split()
        chunks = []
        
        start = 0
        chunk_id = 0
        
        while start < len(words):
            end = start + chunk_size
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            if chunk_text.strip():
                metadata = {
                    'chunk_type': 'overlap_chunk',
                    'chunk_id': chunk_id,
                    'position': f"{start}-{end}"
                }
                chunks.append((chunk_text.strip(), metadata))
                chunk_id += 1
            
            start += (chunk_size - overlap)
        
        return chunks
    
    def process_document(self, filepath: Path) -> List[Dict]:
        """Complete preprocessing pipeline for a single document."""
        
        # Read document
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            raw_text = f.read()
        
        # Clean and normalize
        cleaned_text = self.clean_text(raw_text)
        normalized_text = self.normalize_financial_text(cleaned_text)
        
        # Detect document type
        doc_type = self.detect_document_type(normalized_text, filepath.name)
        
        # Extract base metadata
        base_metadata = self.extract_metadata_from_filename(filepath.name)
        base_metadata['document_type'] = doc_type
        base_metadata['source_file'] = filepath.name
        base_metadata['processed_date'] = datetime.now().isoformat()
        
        # Chunk
        chunks = self.chunk_by_sections(normalized_text, doc_type)
        
        # Enrich with metadata
        processed_chunks = []
        for i, (chunk_text, chunk_metadata) in enumerate(chunks):
            full_metadata = {**base_metadata, **chunk_metadata}
            full_metadata['chunk_index'] = i
            full_metadata['chunk_length'] = len(chunk_text.split())
            
            processed_chunks.append({
                'text': chunk_text,
                'metadata': full_metadata
            })
        
        if self.verbose:
            print(f"Processed {filepath.name}: {len(processed_chunks)} chunks")
        
        return processed_chunks


def preprocess_all_documents(
    input_dir: str = "data/pdfs", 
    output_dir: str = "data/processed",
    verbose: bool = True
) -> Dict:
    """Preprocess all documents and save as JSON."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    preprocessor = FinancialDocumentPreprocessor(verbose=verbose)
    
    # Find all full documents
    documents = list(input_path.glob("*_FULL.txt"))
    
    if verbose:
        print(f"Preprocessing {len(documents)} documents...")
    
    all_processed = {}
    total_chunks = 0
    
    for doc_path in documents:
        processed_chunks = preprocessor.process_document(doc_path)
        
        # Save processed chunks
        ticker = None
        for t in ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META']:
            if t in doc_path.name:
                ticker = t
                break
        
        if ticker:
            output_file = output_path / f"{ticker}_processed.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_chunks, f, indent=2, ensure_ascii=False)
            
            all_processed[ticker] = processed_chunks
            total_chunks += len(processed_chunks)
    
    if verbose:
        print(f"✓ Preprocessing complete: {total_chunks} chunks from {len(documents)} documents")
    
    return all_processed


if __name__ == "__main__":
    preprocess_all_documents()
