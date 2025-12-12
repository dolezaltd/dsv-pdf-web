"""Modul pro zpracování PDF souborů."""
import json
import csv
import re
import base64
import time
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import pdfplumber
import google.generativeai as genai
from .config import GOOGLE_API_KEY, AI_MODEL
from .extract_prompt import EXTRACTION_PROMPT


class PDFProcessor:
    """Třída pro zpracování PDF souborů s využitím AI."""
    
    def __init__(self, logger=None):
        """
        Inicializace procesoru - vždy používá Google Gemini.
        
        Args:
            logger: Instance ExtractionLogger pro logování (volitelné)
        """
        self.model = AI_MODEL
        self.logger = logger
        
        if not GOOGLE_API_KEY:
            raise ValueError(
                "GOOGLE_API_KEY není nastaven!\n"
                "Zkontrolujte soubor .env a ujistěte se, že obsahuje:\n"
                "GOOGLE_API_KEY=vas_api_klic\n\n"
                "API klíč získáte na: https://aistudio.google.com/apikey\n"
                "Podrobnosti najdete v souboru INSTALACE.txt (Krok 1 a Krok 4)."
            )
        genai.configure(api_key=GOOGLE_API_KEY)
        self.google_client = genai.GenerativeModel(self.model)
        
        # Ceník Gemini modelů (ceny za milion tokenů v USD)
        # Zdroj: https://ai.google.dev/pricing
        self.pricing = {
            "gemini-2.5-flash": {
                "input": 0.075,  # $0.075 za milion vstupních tokenů
                "output": 0.30   # $0.30 za milion výstupních tokenů
            },
            "gemini-2.5-flash-lite": {
                "input": 0.10,   # $0.10 za milion vstupních tokenů
                "output": 0.40   # $0.40 za milion výstupních tokenů
            },
            "gemini-1.5-pro": {
                "input": 1.25,   # $1.25 za milion vstupních tokenů (do 200k)
                "output": 10.00, # $10.00 za milion výstupních tokenů (do 200k)
                "input_extended": 2.50,   # $2.50 za milion vstupních tokenů (nad 200k)
                "output_extended": 15.00  # $15.00 za milion výstupních tokenů (nad 200k)
            },
            "gemini-1.5-flash": {
                "input": 0.075,  # $0.075 za milion vstupních tokenů
                "output": 0.30   # $0.30 za milion výstupních tokenů
            }
        }
    
    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> Tuple[float, Dict[str, Any]]:
        """
        Vypočítá náklady na základě počtu tokenů.
        
        Args:
            prompt_tokens: Počet vstupních tokenů
            completion_tokens: Počet výstupních tokenů
            
        Returns:
            Tuple obsahující celkové náklady v USD a slovník s detailními informacemi
        """
        model_key = self.model.lower()
        
        # Najdeme ceník pro model (podporujeme varianty názvů)
        pricing_info = None
        for key in self.pricing.keys():
            if key in model_key or model_key in key:
                pricing_info = self.pricing[key]
                break
        
        if not pricing_info:
            # Výchozí ceník pro neznámé modely (gemini-2.5-flash)
            pricing_info = self.pricing["gemini-2.5-flash"]
        
        # Pro gemini-1.5-pro použijeme extended pricing pokud je přes 200k tokenů
        if "gemini-1.5-pro" in model_key and prompt_tokens > 200000:
            input_price = pricing_info.get("input_extended", pricing_info["input"])
            output_price = pricing_info.get("output_extended", pricing_info["output"])
        else:
            input_price = pricing_info["input"]
            output_price = pricing_info["output"]
        
        # Výpočet nákladů
        input_cost = (prompt_tokens / 1_000_000) * input_price
        output_cost = (completion_tokens / 1_000_000) * output_price
        total_cost = input_cost + output_cost
        
        return total_cost, {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "input_cost_usd": input_cost,
            "output_cost_usd": output_cost,
            "total_cost_usd": total_cost,
            "input_price_per_million": input_price,
            "output_price_per_million": output_price,
            "model": self.model
        }
    
    def print_token_usage(self, usage_info: Dict[str, Any]):
        """
        Vytiskne informace o použití tokenů a nákladech.
        
        Args:
            usage_info: Slovník s informacemi o tokenech a nákladech
        """
        # Převod z USD na CZK (přibližný kurz)
        USD_TO_CZK = 23.5
        total_cost_czk = usage_info['total_cost_usd'] * USD_TO_CZK
        
        # Zaokrouhlení na 2 desetinná místa
        total_cost_czk_rounded = round(total_cost_czk, 2)
        
        print(f"\n💰 Tokeny: {usage_info['total_tokens']:,} | Cena: ~{total_cost_czk_rounded:.2f} Kč\n")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extrahuje text z PDF souboru.
        
        Args:
            pdf_path: Cesta k PDF souboru
            
        Returns:
            Text z PDF jako string
        """
        text_parts = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- PAGE {page_num} ---\n{text}\n")
        
        return "\n".join(text_parts)
    
    def extract_data_with_ai(self, pdf_path: Path) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Extrahuje strukturovaná data z PDF pomocí Google Gemini Vision API.
        
        Args:
            pdf_path: Cesta k PDF souboru
            
        Returns:
            Tuple obsahující seznam slovníků s extrahovanými daty a informace o použití tokenů
        """
        try:
            if not pdf_path:
                raise ValueError("pdf_path je povinný parametr")
            
            # Upravený prompt pro zajištění správného JSON formátu
            system_prompt = EXTRACTION_PROMPT + "\n\nReturn ONLY a JSON array, starting with '[' and ending with ']'."
            
            # Vždy používáme Google Gemini Vision API s PDF souborem
            content, usage_info = self._call_google_gemini(system_prompt, pdf_path)
            
            # Odstranění markdown code bloků pokud jsou přítomny
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Najdi JSON array v textu (může být obklopen textem)
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                content = json_match.group(0)
            
            # Parsování JSON
            try:
                data = json.loads(content)
                # Pokud je to objekt, zkus najít pole uvnitř
                if isinstance(data, dict):
                    # Hledání pole v hodnotách
                    for value in data.values():
                        if isinstance(value, list):
                            return value, usage_info
                    # Pokud není pole, zkus to jako jeden objekt
                    return [data], usage_info
                if not isinstance(data, list):
                    data = [data]
                return data, usage_info
            except json.JSONDecodeError as e:
                print(f"Chyba při parsování JSON: {e}")
                print(f"Obsah odpovědi: {content[:500]}...")
                return [], usage_info
                
        except Exception as e:
            print(f"Chyba při komunikaci s AI modelem: {e}")
            return [], None
    
    def _call_google_gemini(self, system_prompt: str, pdf_path: Path) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Volá Google Gemini API s PDF souborem pomocí File API.
        
        Returns:
            Tuple obsahující textovou odpověď a informace o použití tokenů
        """
        try:
            # Upload PDF souboru přes Gemini File API
            uploaded_file = genai.upload_file(path=str(pdf_path), mime_type="application/pdf")
            
            # Počkej, až se soubor nahraje
            while uploaded_file.state.name == "PROCESSING":
                time.sleep(0.5)
                uploaded_file = genai.get_file(uploaded_file.name)
            
            if uploaded_file.state.name == "FAILED":
                raise ValueError(f"Nahrání souboru selhalo: {uploaded_file.state.name}")
            
            # Příprava promptu
            user_prompt = "Extrahuj všechna data z tohoto PDF dokumentu podle pokynů v systémovém promptu. Vrať pouze validní JSON pole."
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Volání modelu s nahráným souborem
            response = self.google_client.generate_content(
                [full_prompt, uploaded_file],
                generation_config={
                    "temperature": 0.1,  # Nízká teplota pro konzistentní výsledky
                }
            )
            
            usage_info = None
            # Získání informací o tokenech z response
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
                completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
                
                # Výpočet nákladů a zobrazení informací pouze pokud máme alespoň nějaké tokeny
                if prompt_tokens > 0 or completion_tokens > 0:
                    _, usage_info = self.calculate_cost(prompt_tokens, completion_tokens)
                    self.print_token_usage(usage_info)
            
            # Vyčištění - smazání nahráného souboru
            try:
                genai.delete_file(uploaded_file.name)
            except Exception as e:
                print(f"Varování: Nepodařilo se smazat nahráný soubor: {e}")
            
            return response.text.strip(), usage_info
            
        except Exception as e:
            # Pokud File API selže, zkusíme base64 fallback
            print(f"Varování: File API selhalo, zkouším base64 fallback: {e}")
            return self._call_google_gemini_base64(system_prompt, pdf_path)
    
    def _call_google_gemini_base64(self, system_prompt: str, pdf_path: Path) -> Tuple[str, Optional[Dict[str, Any]]]:
        """
        Fallback metoda pro Gemini API s base64 encoded PDF.
        
        Returns:
            Tuple obsahující textovou odpověď a informace o použití tokenů
        """
        # Načtení PDF souboru a převod na base64
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        # Příprava promptu
        user_prompt = "Extrahuj všechna data z tohoto PDF dokumentu podle pokynů v systémovém promptu. Vrať pouze validní JSON pole."
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        
        # Pro base64 musíme použít jiný přístup - Gemini API nepodporuje base64 PDF přímo
        # Místo toho použijeme textovou extrakci
        pdf_text = self.extract_text_from_pdf(pdf_path)
        user_prompt_with_text = f"{user_prompt}\n\nPDF obsah:\n{pdf_text}"
        full_prompt_with_text = f"{system_prompt}\n\n{user_prompt_with_text}"
        
        response = self.google_client.generate_content(
            full_prompt_with_text,
            generation_config={
                "temperature": 0.1,
            }
        )
        
        usage_info = None
        # Získání informací o tokenech z response
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
            
            # Výpočet nákladů a zobrazení informací pouze pokud máme alespoň nějaké tokeny
            if prompt_tokens > 0 or completion_tokens > 0:
                _, usage_info = self.calculate_cost(prompt_tokens, completion_tokens)
                self.print_token_usage(usage_info)
        
        return response.text.strip(), usage_info
    
    def extract_pages_by_type(self, pdf_path: Path, page_types: List[str]) -> Dict[str, List[int]]:
        """
        Identifikuje stránky podle typu (Consignment Note, MRN, atd.).
        
        Args:
            pdf_path: Cesta k PDF souboru
            page_types: Seznam typů stránek k identifikaci (např. ["Consignment Note", "MRN"])
            
        Returns:
            Slovník s typy stránek jako klíče a seznamy čísel stránek jako hodnoty
        """
        result = {page_type: [] for page_type in page_types}
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text_lower = text.lower()
                
                # Identifikace Consignment Note
                if "consignment note" in text_lower and "Consignment Note" in page_types:
                    result["Consignment Note"].append(page_num)
                
                # Identifikace MRN stránky
                if "mrn" in text_lower and "MRN" in page_types:
                    # Kontrola přítomnosti dlouhého kódu (např. "25CZ3O000OO1DAGMB8")
                    has_long_code = any(
                        len(word) >= 15 and word.isalnum() 
                        for word in text.split() 
                        if word
                    )
                    if has_long_code:
                        result["MRN"].append(page_num)
        
        return result
    
    def save_extracted_pages(self, pdf_path: Path, page_numbers: List[int], output_path: Path):
        """
        Uloží specifické stránky z PDF do nového souboru.
        
        Args:
            pdf_path: Cesta k originálnímu PDF
            page_numbers: Seznam čísel stránek k extrakci
            output_path: Cesta k výstupnímu PDF souboru
        """
        from PyPDF2 import PdfReader, PdfWriter
        
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()
        
        for page_num in page_numbers:
            if 1 <= page_num <= len(reader.pages):
                writer.add_page(reader.pages[page_num - 1])
        
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
    
    def convert_to_csv(self, data: List[Dict[str, Any]], output_path: Path):
        """
        Konvertuje seznam slovníků na CSV soubor.
        
        Args:
            data: Seznam slovníků s daty
            output_path: Cesta k výstupnímu CSV souboru
        """
        if not data:
            # Vytvoří prázdný CSV s hlavičkou pokud nejsou žádná data
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['No data extracted'])
            return
        
        # Získání všech možných klíčů ze všech záznamů
        all_keys = set()
        for item in data:
            all_keys.update(item.keys())
        
        # Seřazení klíčů pro konzistentní výstup
        fieldnames = sorted(all_keys)
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in data:
                # Konverze seznamů na řetězce pro CSV
                csv_row = {}
                for key in fieldnames:
                    value = row.get(key, '')
                    if isinstance(value, list):
                        csv_row[key] = '; '.join(str(v) for v in value)
                    elif value is None:
                        csv_row[key] = ''
                    else:
                        csv_row[key] = str(value)
                writer.writerow(csv_row)
    
    def process_pdf(self, pdf_path: Path, output_dir: Path, extraction_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Hlavní metoda pro zpracování PDF souboru.
        
        Args:
            pdf_path: Cesta k PDF souboru
            output_dir: Složka pro výstupní soubory
            extraction_id: ID vytěžení pro logování (volitelné)
            
        Returns:
            Slovník s výsledky zpracování
        """
        start_time = time.time()
        print(f"Zpracovávám soubor: {pdf_path.name}")
        
        # Krok 1: Extrakce dat pomocí Google Gemini Vision API
        print("  → Extrahuji data pomocí Google Gemini Vision API (PDF)...")
        extracted_data, usage_info = self.extract_data_with_ai(pdf_path=pdf_path)
        
        # Krok 3: Identifikace typů stránek (CN a MRN)
        print("  → Identifikuji MRN stránky...")
        page_types = self.extract_pages_by_type(pdf_path, ["Consignment Note", "MRN"])
        found_cn_pages = page_types.get("Consignment Note", [])
        found_mrn_pages = page_types.get("MRN", [])
        
        # Získání MRN stránek z AI extrahovaných dat (pokud jsou k dispozici)
        ai_mrn_pages = []
        if extracted_data:
            for record in extracted_data:
                mrn_pages_value = record.get("mrn_pages", [])
                if mrn_pages_value:
                    # mrn_pages může být číslo, řetězec nebo seznam
                    if isinstance(mrn_pages_value, (int, str)):
                        try:
                            page_num = int(mrn_pages_value)
                            if page_num not in ai_mrn_pages:
                                ai_mrn_pages.append(page_num)
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(mrn_pages_value, list):
                        for page_item in mrn_pages_value:
                            try:
                                page_num = int(page_item)
                                if page_num not in ai_mrn_pages:
                                    ai_mrn_pages.append(page_num)
                            except (ValueError, TypeError):
                                pass
        
        # Pokud AI extrahovala MRN stránky, použijeme je (mají prioritu)
        if ai_mrn_pages:
            print(f"  → Nalezeno {len(ai_mrn_pages)} MRN stránek z AI extrakce: {sorted(ai_mrn_pages)}")
            found_mrn_pages = sorted(ai_mrn_pages)
            page_types["MRN"] = found_mrn_pages
        elif found_mrn_pages:
            print(f"  → Nalezeno {len(found_mrn_pages)} MRN stránek pomocí textové detekce: {found_mrn_pages}")
        
        # Aktualizace mrn_pages v extrahovaných datech pomocí spolehlivé metody
        # Přiřazení MRN stránek ke Consignment Notes podle pořadí v dokumentu
        if extracted_data:
            # Pokud AI už extrahovala mrn_pages, zachováme je (nepřepisujeme)
            if not ai_mrn_pages and not found_mrn_pages:
                # Pokud nebyly nalezeny žádné MRN stránky ani od AI ani textově, nastavíme prázdné hodnoty
                for record in extracted_data:
                    if "mrn_pages" not in record or not record.get("mrn_pages"):
                        record["mrn_pages"] = []
            elif found_mrn_pages and not ai_mrn_pages:
                # Pokud máme MRN stránky z textové detekce, ale ne z AI, přiřadíme je podle pořadí
                if found_cn_pages and len(found_cn_pages) == len(extracted_data):
                    # Přiřazení MRN stránek, které následují po každém CN
                    for i, cn_page_num in enumerate(found_cn_pages):
                        # Najdeme MRN stránky mezi tímto CN a dalším CN (nebo koncem dokumentu)
                        next_cn_page = found_cn_pages[i + 1] if i + 1 < len(found_cn_pages) else float('inf')
                        assigned_mrn_pages = [p for p in found_mrn_pages if cn_page_num < p < next_cn_page]
                        
                        if i < len(extracted_data):
                            if len(assigned_mrn_pages) == 1:
                                extracted_data[i]["mrn_pages"] = assigned_mrn_pages[0]
                            elif len(assigned_mrn_pages) > 1:
                                extracted_data[i]["mrn_pages"] = assigned_mrn_pages
                            else:
                                extracted_data[i]["mrn_pages"] = []
                else:
                    # Fallback: rozdělení MRN stránek rovnoměrně mezi CN
                    mrn_pages_per_cn = len(found_mrn_pages) // len(extracted_data) if extracted_data else 0
                    remainder = len(found_mrn_pages) % len(extracted_data) if extracted_data else 0
                    
                    mrn_index = 0
                    for i, record in enumerate(extracted_data):
                        pages_for_this_cn = mrn_pages_per_cn + (1 if i < remainder else 0)
                        
                        if mrn_index < len(found_mrn_pages):
                            assigned_pages = found_mrn_pages[mrn_index:mrn_index + pages_for_this_cn]
                            record["mrn_pages"] = assigned_pages if len(assigned_pages) > 1 else (assigned_pages[0] if assigned_pages else [])
                            mrn_index += pages_for_this_cn
                        else:
                            record["mrn_pages"] = []
        
        # Krok 4: Vytvoření výstupní složky s názvem PDF (bez přípony)
        output_folder = output_dir / pdf_path.stem
        output_folder.mkdir(parents=True, exist_ok=True)
        
        # Krok 5: Uložení CSV s extrahovanými daty
        csv_path = output_folder / f"{pdf_path.stem}.csv"
        self.convert_to_csv(extracted_data, csv_path)
        print(f"  → Uloženo: {csv_path}")
        
        # Krok 6: Extrakt MRN stránek do samostatného PDF
        mrn_pdf_path = None
        mrn_pages_to_extract = page_types.get("MRN", [])
        if mrn_pages_to_extract:
            mrn_pdf_path = output_folder / f"{pdf_path.stem}_MRN.pdf"
            self.save_extracted_pages(pdf_path, mrn_pages_to_extract, mrn_pdf_path)
            print(f"  → Uloženo: {mrn_pdf_path} ({len(mrn_pages_to_extract)} stránek)")
        else:
            print("  → Varování: Nebyly nalezeny žádné MRN stránky")
        
        processing_time = time.time() - start_time
        
        # Logování úspěšného vytěžení
        if self.logger and extraction_id and usage_info:
            output_files_dict = {
                "csv": str(csv_path),
                "mrn_pdf": str(mrn_pdf_path) if mrn_pdf_path else None
            }
            self.logger.log_extraction_success(
                extraction_id=extraction_id,
                pdf_filename=pdf_path.name,
                usage_info=usage_info,
                extracted_records_count=len(extracted_data) if extracted_data else 0,
                processing_time=processing_time,
                output_files=output_files_dict
            )
        
        return {
            "extracted_data": extracted_data,
            "page_types": page_types,
            "output_folder": str(output_folder),
            "output_files": {
                "csv": str(csv_path),
                "mrn_pdf": str(mrn_pdf_path) if mrn_pdf_path else None
            },
            "usage_info": usage_info,
            "processing_time": processing_time
        }

