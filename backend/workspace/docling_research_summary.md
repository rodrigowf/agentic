# Docling: Comprehensive Research Summary

**Research Date:** 2025-11-30
**Purpose:** File Manager Agent implementation brainstorming
**Status:** Complete

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Installation & Setup](#installation--setup)
4. [Core API & Usage](#core-api--usage)
5. [Document Formats](#document-formats)
6. [DoclingDocument Data Model](#doclingdocument-data-model)
7. [Chunking for RAG](#chunking-for-rag)
8. [Table Extraction](#table-extraction)
9. [OCR Capabilities](#ocr-capabilities)
10. [Image Processing](#image-processing)
11. [Export Formats](#export-formats)
12. [Integration Ecosystem](#integration-ecosystem)
13. [Configuration Options](#configuration-options)
14. [Performance & Optimization](#performance--optimization)
15. [Use Cases for File Manager Agent](#use-cases-for-file-manager-agent)
16. [References & Links](#references--links)

---

## Overview

**Docling** is an open-source document processing framework developed by IBM Research Zurich's AI for Knowledge team and hosted by the LF AI & Data Foundation. It transforms diverse document formats into structured, AI-ready data ideal for Generative AI and agentic applications.

**Key Value Proposition:**
- Processes documents **up to 30x faster** than traditional OCR-based methods
- Provides **unified representation** across all document types
- Built for **RAG (Retrieval Augmented Generation)** workflows
- **Local execution** capability for sensitive data and air-gapped environments

**License:** MIT (core library), individual models may have different licenses

---

## Key Features

### 1. **Multi-Format Support**
- **Documents:** PDF, DOCX, PPTX, XLSX, HTML
- **Audio:** WAV, MP3 (with ASR)
- **Video:** WebVTT (Web Video Text Tracks)
- **Images:** PNG, TIFF, JPEG, and more

### 2. **Advanced PDF Understanding**
- Page layout detection and reading order
- Table structure recognition
- Formula extraction
- Code block detection
- Image classification
- OCR for scanned documents

### 3. **AI-Powered Processing**
- **Visual Language Models (VLM):** Including Granite-Docling (258M parameters)
- **Automatic Speech Recognition (ASR):** For audio files
- **Structured Information Extraction:** (Beta) Extract specific data patterns

### 4. **RAG-Ready Output**
- Semantic chunking with **HybridChunker**
- Tokenization-aware refinements
- Direct integration with LangChain, LlamaIndex, Crew AI, Haystack
- Multiple export formats (Markdown, HTML, JSON, DocTags)

### 5. **Recent Additions (2025)**
- **Heron layout model:** Faster PDF parsing
- **MCP server:** For agentic applications
- **Granite-Docling VLM:** Ultra-compact (258M) model for document conversion

---

## Installation & Setup

### Basic Installation

```bash
pip install docling
```

**Platforms:** macOS, Linux, Windows (x86_64 and arm64)

### With Chunking Support

```bash
# For HuggingFace tokenizers
pip install 'docling-core[chunking]'

# For OpenAI tokenizers (tiktoken)
pip install 'docling-core[chunking-openai]'
```

### Dependencies
- Python 3.8+
- Pydantic v2 (for data validation)
- Transformers (for tokenization)
- tiktoken (optional, for OpenAI tokenizers)

---

## Core API & Usage

### Basic Document Conversion

```python
from docling.document_converter import DocumentConverter

# Initialize converter
converter = DocumentConverter()

# Convert document (local path or URL)
source = "https://arxiv.org/pdf/2408.09869"  # or local file path
result = converter.convert(source)

# Export to Markdown
markdown_text = result.document.export_to_markdown()
print(markdown_text)
```

### CLI Usage

```bash
# Basic conversion
docling https://arxiv.org/pdf/2206.01062

# Vision-based parsing with VLM
docling --pipeline vlm --vlm-model granite_docling [url]
```

### Key Classes

- **`DocumentConverter`** - Main conversion engine
- **`DoclingDocument`** - Unified document representation (Pydantic model)
- **`HybridChunker`** - Semantic document chunking for RAG
- **`PdfPipelineOptions`** - Configuration for PDF processing

---

## Document Formats

### Supported Input Formats

| Format | Extension | Features |
|--------|-----------|----------|
| PDF | `.pdf` | Layout, tables, OCR, formulas, images |
| Word | `.docx` | Text, tables, images, structure |
| PowerPoint | `.pptx` | Slides, text, images |
| Excel | `.xlsx` | Tables, data extraction |
| HTML | `.html` | Web content, structure |
| Audio | `.wav`, `.mp3` | ASR transcription |
| Video | `.vtt` | Subtitle/caption extraction |
| Images | `.png`, `.jpg`, `.tiff`, etc. | OCR, visual content |

### Format-Specific Features

- **PDF:** Advanced layout analysis, reading order preservation, table structure
- **DOCX:** Hierarchical structure, styles, embedded media
- **XLSX:** Cell-level data, formulas, multi-sheet support
- **Images:** OCR with multiple engines, orientation correction

---

## DoclingDocument Data Model

### Overview
`DoclingDocument` is a **Pydantic datatype** introduced in Docling v2, providing a unified representation for all document types.

### Top-Level Fields (Content Items)

```python
class DoclingDocument:
    texts: List[TextItem]           # Paragraphs, headings, equations
    tables: List[TableItem]         # Tables with structural annotations
    pictures: List[PictureItem]     # Images with metadata
    key_value_items: List[KeyValueItem]  # Key-value pairs
```

All items inherit from `DocItem` base type.

### Content Structure (Tree Organization)

```python
class DoclingDocument:
    body: NodeItem                  # Main document content tree
    furniture: NodeItem             # Headers, footers, page numbers
    groups: List[NodeItem]          # Chapters, sections, lists
```

**Key Features:**
- **Parent-child references:** Using JSON pointers
- **Reading order:** Preserved through `body` tree child ordering
- **Layout information:** Bounding boxes for visual elements
- **Hierarchical structure:** Nested grouping and nesting

### Example Structure

```
DoclingDocument
├── body (NodeItem)
│   ├── Heading (TextItem)
│   ├── Paragraph (TextItem)
│   ├── Table (TableItem)
│   └── List (NodeItem)
│       ├── ListItem (TextItem)
│       └── ListItem (TextItem)
├── furniture (NodeItem)
│   ├── Header (TextItem)
│   └── Footer (TextItem)
└── tables (list)
    └── TableItem with structure
```

---

## Chunking for RAG

### Purpose
Transform `DoclingDocument` into smaller, semantically meaningful segments that:
- Fit within LLM context windows
- Maintain semantic coherence
- Preserve document structure
- Enable effective retrieval

### HybridChunker

The **HybridChunker** combines:
1. **Document structure awareness** (hierarchical chunking)
2. **Tokenization awareness** (size constraints)

### Basic Usage

```python
from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from transformers import AutoTokenizer

# Configure tokenizer
EMBED_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MAX_TOKENS = 512

tokenizer = HuggingFaceTokenizer(
    tokenizer=AutoTokenizer.from_pretrained(EMBED_MODEL_ID),
    max_tokens=MAX_TOKENS,
)

# Create chunker
chunker = HybridChunker(
    tokenizer=tokenizer,
    merge_peers=True,  # Merge undersized peer chunks
)

# Chunk document
chunk_iter = chunker.chunk(dl_doc=doc)
chunks = list(chunk_iter)
```

### OpenAI Tokenizer Alternative

```python
import tiktoken
from docling_core.transforms.chunker.tokenizer.openai import OpenAITokenizer

tokenizer = OpenAITokenizer(
    tokenizer=tiktoken.encoding_for_model("gpt-4o"),
    max_tokens=128 * 1024,  # Context window length
)

chunker = HybridChunker(tokenizer=tokenizer)
```

### Chunking Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| **Hybrid** | Structure + tokenization | Most RAG use cases |
| **Hierarchical** | Document structure only | Preserving document organization |
| **Token-based** | Fixed token sizes | Uniform chunk sizes |
| **Custom** | User-defined boundaries | Specialized workflows |

### Key Parameters

- **`max_tokens`** - Maximum tokens per chunk
- **`merge_peers`** - Combine undersized sibling chunks (default: True)
- **`tokenizer`** - Tokenizer matching your embedding model

### Export Modes for RAG

```python
from docling.datamodel.base_models import ExportType

# Option 1: Export as single markdown document
converter.convert(source, export_type=ExportType.MARKDOWN)

# Option 2: Export as pre-chunked documents (default for RAG)
converter.convert(source, export_type=ExportType.DOC_CHUNKS)
```

**ExportType.DOC_CHUNKS** - Each chunk becomes a separate retrievable document

---

## Table Extraction

### Capabilities

Docling's **TableFormer AI model** provides:
- **Logical structure prediction:** Row and column organization
- **Cell classification:** Headers (row/column) vs. body cells
- **Spanning cells:** Rowspan and colspan detection
- **Structure reassembly:** Reconstructs table hierarchy

### Configuration

```python
from docling.document_converter import DocumentConverter, PdfPipelineOptions

pipeline_options = PdfPipelineOptions()
pipeline_options.do_table_structure = True  # Enable table extraction
pipeline_options.do_cell_matching = True    # Match cells to structure

converter = DocumentConverter(
    pipeline_options=pipeline_options
)
```

### Output Formats

- **Pandas DataFrame:** Direct table-to-DataFrame conversion
- **CSV:** Ready-to-save tabular data
- **Structured JSON:** With cell coordinates and metadata
- **Markdown tables:** Human-readable format

### Example Output

```python
# Access tables from DoclingDocument
for table in result.document.tables:
    df = table.export_to_dataframe()  # Pandas DataFrame
    csv = table.export_to_csv()       # CSV string
    print(df)
```

---

## OCR Capabilities

### Supported OCR Engines

1. **Tesseract** - Traditional, widely supported
2. **EasyOCR** - Deep learning-based, high accuracy
3. **RapidOCR** - Fast inference, good balance

### Configuration

```python
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True                  # Enable OCR
pipeline_options.ocr_options.lang = ["eng"]     # Language(s)
pipeline_options.ocr_options.force_full_page_ocr = False  # OCR strategy

converter = DocumentConverter(
    pipeline_options=pipeline_options
)
```

### OCR Features

- **Automatic detection:** Skip OCR for digital PDFs with embedded text
- **Language support:** Multi-language detection and extraction
- **Orientation correction:** Automatic rotation handling
- **Quality thresholds:** Configurable confidence levels
- **Region-based OCR:** Process specific page regions

### Smart OCR Behavior

```python
# Digital PDF with text layer → OCR skipped (faster)
# Scanned document/image → OCR activated automatically
```

---

## Image Processing

### Image Extraction

```python
pipeline_options = PdfPipelineOptions()
pipeline_options.generate_picture_images = True  # Extract images as PIL objects

converter = DocumentConverter(
    pipeline_options=pipeline_options
)

result = converter.convert(source)

# Access extracted images
for picture in result.document.pictures:
    pil_image = picture.image  # PIL Image object
    bbox = picture.prov[0].bbox  # Bounding box
    # Process image...
```

### Image Classification

Docling automatically classifies images:
- **Figures:** Charts, diagrams, photos
- **Logos:** Company branding
- **Decorative:** Background elements

### Image Features

- **Bounding box localization:** Precise coordinates on page
- **PIL object extraction:** Ready for vision models
- **Metadata preservation:** Source, page number, position
- **Layout integration:** Images maintain document flow context

---

## Export Formats

### Markdown

```python
markdown = result.document.export_to_markdown()
```

**Features:**
- Headings preserved as `#`, `##`, etc.
- Tables as markdown tables
- Lists with proper indentation
- Code blocks with syntax markers

### HTML

```python
html = result.document.export_to_html()
```

**Features:**
- Semantic HTML5 tags
- CSS classes for styling
- Tables as `<table>` elements
- Images as `<img>` with base64 encoding

### JSON (Lossless)

```python
json_data = result.document.export_to_dict()
```

**Features:**
- Complete document structure
- All metadata preserved
- Bounding boxes included
- Provenance information

### DocTags

Custom XML-like format for document elements.

---

## Integration Ecosystem

### LangChain

```python
from langchain_community.document_loaders import DoclingLoader

loader = DoclingLoader(
    file_path="document.pdf",
    export_type=ExportType.DOC_CHUNKS  # Pre-chunk for RAG
)
docs = loader.load()
```

### LlamaIndex

```python
from llama_index.readers.docling import DoclingReader

reader = DoclingReader()
documents = reader.load_data(file_path="document.pdf")
```

### Haystack

Direct integration with Haystack document stores and pipelines.

### Crew AI

Use as document processor in multi-agent workflows.

---

## Configuration Options

### PdfPipelineOptions

```python
from docling.document_converter import PdfPipelineOptions

options = PdfPipelineOptions()

# OCR settings
options.do_ocr = True
options.ocr_options.lang = ["eng", "fra"]
options.ocr_options.force_full_page_ocr = False

# Table extraction
options.do_table_structure = True
options.do_cell_matching = True

# Image handling
options.generate_picture_images = True
options.generate_page_images = False
options.images_scale = 1.0  # Resolution multiplier

# Performance optimization
options.accelerator_options.device = "cuda"  # Use GPU
options.enable_parallel_processing = True

# Page range limits
options.page_range = (1, 10)  # Process pages 1-10
options.max_num_pages = 100   # Limit total pages
```

### DocumentConverter Options

```python
converter = DocumentConverter(
    pipeline_options=options,
    format_options={
        "pdf": options,
        # Add format-specific options
    }
)
```

---

## Performance & Optimization

### Speed Improvements

- **Up to 30x faster** than traditional OCR methods
- **Heron layout model:** New faster PDF parsing (2025)
- **Parallel processing:** Multi-core support
- **Smart OCR:** Skip for digital PDFs

### Optimization Strategies

1. **Disable unused features:**
   ```python
   options.do_table_structure = False  # Skip if no tables
   options.generate_page_images = False  # Save memory
   ```

2. **Limit page range:**
   ```python
   options.page_range = (1, 50)  # Process first 50 pages
   options.max_num_pages = 100
   ```

3. **Reduce image resolution:**
   ```python
   options.images_scale = 0.5  # 50% resolution
   ```

4. **Use GPU acceleration:**
   ```python
   options.accelerator_options.device = "cuda"
   ```

5. **Enable parallel processing:**
   ```python
   options.enable_parallel_processing = True
   ```

### Memory Management

- Stream large documents instead of loading entirely
- Process in batches for bulk operations
- Clear converter cache periodically

---

## Use Cases for File Manager Agent

### 1. **Intelligent Document Indexing**

**Integration:** Use Docling to process uploaded documents before indexing to vector store.

```python
# Pseudo-code for FileManager tool
def index_file_to_vectorstore(filepath: str) -> str:
    # Convert document with Docling
    converter = DocumentConverter()
    result = converter.convert(filepath)

    # Chunk for RAG
    chunker = HybridChunker(tokenizer=tokenizer)
    chunks = list(chunker.chunk(result.document))

    # Index each chunk to ChromaDB
    for chunk in chunks:
        collection.add(
            documents=[chunk.text],
            metadatas=[{
                "filepath": filepath,
                "chunk_id": chunk.meta.doc_items[0].self_ref,
                "file_type": detect_type(filepath)
            }]
        )

    return f"Indexed {len(chunks)} chunks from {filepath}"
```

**Benefits:**
- ✅ Handles PDF, DOCX, PPTX, XLSX, HTML, images
- ✅ Preserves document structure
- ✅ Extracts tables as structured data
- ✅ OCR for scanned documents
- ✅ Semantic chunking for better retrieval

### 2. **Semantic File Search with Structure**

**Integration:** Search not just by content, but by document structure.

```python
def search_files_semantic(query: str, filter_type: str = None) -> str:
    # Search ChromaDB with metadata filters
    results = collection.query(
        query_texts=[query],
        n_results=5,
        where={"file_type": filter_type} if filter_type else None
    )

    # Return results with document context
    for result in results:
        # Docling metadata includes structure info
        print(f"Found in {result.metadata['filepath']}")
        print(f"Section: {result.metadata.get('section', 'Unknown')}")
        print(f"Content: {result.text}")
```

**Use Cases:**
- "Find tables about Q3 revenue" → Returns table chunks
- "Search presentations about AI" → PPTX content
- "Find code snippets in documentation" → Code blocks

### 3. **Document Understanding & Summarization**

**Integration:** Use Docling's structure for intelligent summarization.

```python
def summarize_file(filepath: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(filepath)

    # Extract structured elements
    doc = result.document

    summary = {
        "title": doc.texts[0].text if doc.texts else "Untitled",
        "num_pages": len(doc.pages),
        "num_tables": len(doc.tables),
        "num_images": len(doc.pictures),
        "sections": [t.text for t in doc.texts if t.label == "heading"],
        "key_points": extract_key_sentences(doc)
    }

    return format_summary(summary)
```

### 4. **Table Extraction Tool**

**Integration:** Dedicated tool for extracting and analyzing tables.

```python
def extract_tables_from_file(filepath: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(filepath)

    tables_data = []
    for i, table in enumerate(result.document.tables):
        df = table.export_to_dataframe()
        csv_path = f"workspace/tables/{filepath.stem}_table_{i}.csv"
        df.to_csv(csv_path)
        tables_data.append({
            "table_index": i,
            "rows": len(df),
            "columns": len(df.columns),
            "csv_path": csv_path
        })

    return f"Extracted {len(tables_data)} tables: {tables_data}"
```

**Use Cases:**
- Extract financial tables from PDFs
- Convert Excel sheets to searchable format
- Analyze table structure across documents

### 5. **Multi-Format File Organization**

**Integration:** Use Docling to understand content for organization.

```python
def suggest_file_organization(directory: str) -> str:
    files = list_files(directory)
    converter = DocumentConverter()

    categorization = {}
    for file in files:
        result = converter.convert(file)

        # Analyze content
        has_tables = len(result.document.tables) > 0
        has_code = any(t.label == "code" for t in result.document.texts)
        topic = classify_topic(result.document.texts)

        # Suggest folder
        if has_tables:
            folder = "data_reports"
        elif has_code:
            folder = "technical_docs"
        else:
            folder = f"documents/{topic}"

        categorization[file] = folder

    return format_suggestions(categorization)
```

### 6. **Duplicate Detection Across Formats**

**Integration:** Compare document content regardless of format.

```python
def find_duplicate_files(directory: str) -> str:
    files = list_files(directory)
    converter = DocumentConverter()

    content_hashes = {}
    for file in files:
        result = converter.convert(file)
        # Use text content for hashing
        content = result.document.export_to_markdown()
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash in content_hashes:
            content_hashes[content_hash].append(file)
        else:
            content_hashes[content_hash] = [file]

    duplicates = {k: v for k, v in content_hashes.items() if len(v) > 1}
    return format_duplicates(duplicates)
```

**Use Cases:**
- Find same report in PDF and DOCX
- Detect duplicate presentations
- Identify redundant documentation

### 7. **Audio/Video Transcription Integration**

**Integration:** Extend FileManager to handle multimedia.

```python
def transcribe_audio_file(filepath: str) -> str:
    converter = DocumentConverter()
    result = converter.convert(filepath)  # WAV/MP3

    # Docling uses ASR to transcribe
    transcript = result.document.export_to_markdown()

    # Save transcript
    transcript_path = filepath.with_suffix('.txt')
    with open(transcript_path, 'w') as f:
        f.write(transcript)

    # Index to vector store
    index_file_to_vectorstore(transcript_path)

    return f"Transcribed and indexed: {transcript_path}"
```

---

## References & Links

### Official Documentation
- **Main Docs:** [https://docling-project.github.io/docling/](https://docling-project.github.io/docling/)
- **GitHub Repository:** [https://github.com/docling-project/docling](https://github.com/docling-project/docling)
- **DoclingDocument Concepts:** [https://docling-project.github.io/docling/concepts/docling_document/](https://docling-project.github.io/docling/concepts/docling_document/)
- **Chunking Concepts:** [https://docling-project.github.io/docling/concepts/chunking/](https://docling-project.github.io/docling/concepts/chunking/)

### Examples & Tutorials
- **Hybrid Chunking:** [https://docling-project.github.io/docling/examples/hybrid_chunking/](https://docling-project.github.io/docling/examples/hybrid_chunking/)
- **RAG with LangChain:** [https://docling-project.github.io/docling/examples/rag_langchain/](https://docling-project.github.io/docling/examples/rag_langchain/)
- **RAG with Haystack:** [https://docling-project.github.io/docling/examples/rag_haystack/](https://docling-project.github.io/docling/examples/rag_haystack/)
- **Advanced Chunking:** [https://docling-project.github.io/docling/examples/advanced_chunking_and_serialization/](https://docling-project.github.io/docling/examples/advanced_chunking_and_serialization/)

### Integrations
- **LangChain Docs:** [https://docs.langchain.com/oss/python/integrations/document_loaders/docling](https://docs.langchain.com/oss/python/integrations/document_loaders/docling)
- **LangChain Tutorial:** [Building a RAG with Docling and LangChain](https://alain-airom.medium.com/building-a-rag-with-docling-and-langchain-c2aef50c9b43)
- **DataCamp Guide:** [Docling: A Guide to Building a Document Intelligence App](https://www.datacamp.com/tutorial/docling)

### Deep Dives
- **Document Chunking:** [https://deepwiki.com/docling-project/docling/8.2-document-chunking](https://deepwiki.com/docling-project/docling/8.2-document-chunking)
- **Hybrid Chunking Core:** [https://github.com/docling-project/docling-core/blob/main/docling_core/transforms/chunker/hybrid_chunker.py](https://github.com/docling-project/docling-core/blob/main/docling_core/transforms/chunker/hybrid_chunker.py)
- **OCR Integration:** [Using Docling's OCR features with RapidOCR](https://dev.to/aairom/using-doclings-ocr-features-with-rapidocr-29hd)

### Models
- **Granite-Docling (2025):** [IBM Granite-Docling: End-to-end document understanding](https://www.ibm.com/new/announcements/granite-docling-end-to-end-document-conversion)
- **SmolDocling (Preview):** [https://huggingface.co/docling-project/SmolDocling-256M-preview](https://huggingface.co/docling-project/SmolDocling-256M-preview)

### Community & Discussions
- **GitHub Discussions:** [https://github.com/docling-project/docling/discussions](https://github.com/docling-project/docling/discussions)
- **HybridChunker with tiktoken:** [https://github.com/docling-project/docling/discussions/1031](https://github.com/docling-project/docling/discussions/1031)
- **Hybrid Chunker Announcement:** [https://github.com/docling-project/docling/discussions/548](https://github.com/docling-project/docling/discussions/548)

### Articles & Blogs
- **Introduction to Docling:** [https://heidloff.net/article/docling/](https://heidloff.net/article/docling/)
- **Document Intelligence Guide:** [https://atalupadhyay.wordpress.com/2025/08/07/document-intelligence-guide-to-docling-for-ai-ready-data-processing/](https://atalupadhyay.wordpress.com/2025/08/07/document-intelligence-guide-to-docling-for-ai-ready-data-processing/)
- **Simplifying Document Processing:** [https://medium.com/@tam.tamanna18/simplifying-document-processing-with-docling-for-ai-applications-6fbcc5139522](https://medium.com/@tam.tamanna18/simplifying-document-processing-with-docling-for-ai-applications-6fbcc5139522)
- **Document Question Answering:** [https://www.ibm.com/think/tutorials/build-document-question-answering-system-with-docling-and-granite](https://www.ibm.com/think/tutorials/build-document-question-answering-system-with-docling-and-granite)
- **Multimodal RAG Tutorial:** [https://www.ibm.com/think/tutorials/build-multimodal-rag-langchain-with-docling-granite](https://www.ibm.com/think/tutorials/build-multimodal-rag-langchain-with-docling-granite)

---

## Brainstorming Notes for File Manager Agent

### Why Docling?

1. **Comprehensive format support** - Single tool for PDF, DOCX, PPTX, XLSX, HTML, images
2. **Structure preservation** - Maintains document hierarchy, not just text extraction
3. **RAG-ready** - Built-in chunking and vector store integration
4. **Table extraction** - Critical for data documents
5. **OCR support** - Handles scanned documents automatically
6. **Fast** - 30x faster than traditional methods
7. **Local execution** - Privacy-friendly, no cloud dependency

### Integration Points

- **`index_file_to_vectorstore()`** - Use Docling before ChromaDB indexing
- **`summarize_file()`** - Leverage structure for better summaries
- **`analyze_file_structure()`** - Use DoclingDocument model
- **`search_files_semantic()`** - Enhanced with Docling's chunking
- **New tool:** `extract_tables_from_file()` - Export tables to CSV/DataFrame

### Considerations

- **Installation overhead** - Requires additional dependencies
- **Model downloads** - VLM models (~258MB) for advanced features
- **Processing time** - Still takes time for large documents
- **Format limitations** - Some exotic formats may not be supported
- **Memory usage** - Large documents with images can be memory-intensive

### Recommended Approach

1. **Start simple** - Basic CRUD operations without Docling
2. **Add Docling gradually** - Integrate for indexing operations
3. **Make it optional** - Allow FileManager to work with/without Docling
4. **Focus on common formats** - PDF, DOCX, XLSX as priority

### Next Steps

1. Review Task 2 plan with Docling in mind
2. Decide which tools should use Docling
3. Design configuration for enabling/disabling Docling features
4. Plan testing strategy with various document types
5. Consider Docling as enhancement, not requirement

---

**End of Research Summary**

*This document should be referenced when implementing the File Manager Agent to ensure we leverage Docling's capabilities effectively.*
