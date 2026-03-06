import requests
import json
import re
import numpy as np
from collections import Counter, defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import hashlib
import os
from difflib import SequenceMatcher
from PIL import Image
import io

class AcademicDishonestyDetector:
    def __init__(self):
        self.answer_scripts = []
        self.suspicious_pairs = []
        self.stylometric_features = {}
        
    def compress_image(self, file_path, max_size_kb=900):
        """Compress image to reduce file size for OCR API"""
        try:
            # Check current file size
            file_size_kb = os.path.getsize(file_path) / 1024
            if file_size_kb <= max_size_kb:
                return file_path  # No compression needed
                
            print(f"Compressing image: {file_path} (Current size: {file_size_kb:.1f} KB)")
            
            with Image.open(file_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Calculate compression quality
                quality = 95
                while quality > 10:
                    # Save to buffer with current quality
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    compressed_size_kb = len(buffer.getvalue()) / 1024
                    
                    if compressed_size_kb <= max_size_kb or quality <= 20:
                        # Save compressed image
                        compressed_path = file_path.replace('.', '_compressed.')
                        with open(compressed_path, 'wb') as f:
                            f.write(buffer.getvalue())
                        print(f"✓ Compressed to: {compressed_size_kb:.1f} KB (quality: {quality}%)")
                        return compressed_path
                    
                    quality -= 5
                
                # If still too large, resize the image
                print("File still too large, resizing image...")
                width, height = img.size
                new_width = width // 2
                new_height = height // 2
                img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                img_resized.save(buffer, format='JPEG', quality=80, optimize=True)
                compressed_path = file_path.replace('.', '_compressed.')
                with open(compressed_path, 'wb') as f:
                    f.write(buffer.getvalue())
                
                final_size_kb = os.path.getsize(compressed_path) / 1024
                print(f"✓ Resized and compressed to: {final_size_kb:.1f} KB")
                return compressed_path
                
        except Exception as e:
            print(f"Error compressing image {file_path}: {str(e)}")
            return file_path  # Return original if compression fails
    
    def process_scripts_with_ocr(self, file_paths, api_key):
        """Process multiple answer scripts using OCR with file size handling"""
        processed_scripts = []
        
        for idx, file_path in enumerate(file_paths):
            print(f"Processing {file_path}...")
            
            # Check file size and compress if needed
            file_size_kb = os.path.getsize(file_path) / 1024
            if file_size_kb > 900:  # Compress if over 900KB to be safe
                processed_file_path = self.compress_image(file_path)
            else:
                processed_file_path = file_path
            
            # Use OCR function
            result = self.ocr_space_file(filename=processed_file_path, language="eng", api_key=api_key)
            text = self.extract_text(result)
            
            # Clean up compressed file if it was created
            if processed_file_path != file_path and os.path.exists(processed_file_path):
                try:
                    os.remove(processed_file_path)
                except:
                    pass
            
            if text.startswith("Error"):
                print(f"OCR failed for {file_path}: {text}")
                continue
                
            script_data = {
                'id': idx + 1,
                'filename': file_path,
                'raw_text': text,
                'cleaned_text': self.clean_text(text),
                'answers': self.extract_answers(text),
                'hash': self.generate_text_hash(text),
                'processing_date': datetime.now().isoformat()
            }
            
            # Extract stylometric features
            script_data['stylometric'] = self.extract_stylometric_features(text)
            
            processed_scripts.append(script_data)
            print(f"✓ Processed script {idx + 1}: {len(text)} characters")
            
        self.answer_scripts = processed_scripts
        return processed_scripts
    
    def detect_identical_wrong_answers(self):
        """Flag scripts with identical wrong answers"""
        suspicious_pairs = []
        
        for i, script1 in enumerate(self.answer_scripts):
            for j, script2 in enumerate(self.answer_scripts):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                    
                common_wrong_answers = self.find_common_wrong_answers(
                    script1['answers'], 
                    script2['answers']
                )
                
                if common_wrong_answers:
                    similarity_score = len(common_wrong_answers) / max(len(script1['answers']), len(script2['answers']))
                    
                    if similarity_score > 0.3:  # Threshold for suspicion
                        suspicious_pairs.append({
                            'script1_id': script1['id'],
                            'script2_id': script2['id'],
                            'script1_file': script1['filename'],
                            'script2_file': script2['filename'],
                            'common_wrong_answers': common_wrong_answers,
                            'similarity_score': similarity_score,
                            'detection_method': 'identical_wrong_answers'
                        })
        
        return suspicious_pairs
    
    def detect_rare_answer_patterns(self):
        """Identify rare answer patterns that might indicate collusion"""
        all_answers = []
        question_answers = defaultdict(list)
        
        # Collect all answers by question
        for script in self.answer_scripts:
            for q_num, answer in script['answers'].items():
                question_answers[q_num].append(answer)
        
        # Find rare patterns
        rare_patterns = []
        for script in self.answer_scripts:
            script_rare_answers = []
            
            for q_num, answer in script['answers'].items():
                answer_frequency = question_answers[q_num].count(answer)
                total_scripts = len(self.answer_scripts)
                
                # Consider answer rare if it appears in less than 10% of scripts
                if answer_frequency / total_scripts < 0.1 and answer_frequency > 0:
                    script_rare_answers.append({
                        'question': q_num,
                        'answer': answer,
                        'frequency': answer_frequency,
                        'percentage': (answer_frequency / total_scripts) * 100
                    })
            
            if script_rare_answers:
                rare_patterns.append({
                    'script_id': script['id'],
                    'filename': script['filename'],
                    'rare_answers': script_rare_answers,
                    'detection_method': 'rare_answer_patterns'
                })
        
        return rare_patterns
    
    def perform_stylometric_analysis(self):
        """Analyze writing style inconsistencies"""
        stylometric_suspicions = []
        
        for script in self.answer_scripts:
            features = script['stylometric']
            inconsistencies = []
            
            # Check for unusual vocabulary variations
            if features['avg_sentence_length'] > 50 or features['avg_sentence_length'] < 5:
                inconsistencies.append(f"Unusual average sentence length: {features['avg_sentence_length']:.2f}")
            
            if features['vocabulary_richness'] < 0.3:
                inconsistencies.append(f"Low vocabulary richness: {features['vocabulary_richness']:.2f}")
            
            if features['punctuation_density'] > 0.2 or features['punctuation_density'] < 0.01:
                inconsistencies.append(f"Unusual punctuation density: {features['punctuation_density']:.2f}")
            
            # Check for unusual word length patterns
            if features['avg_word_length'] > 8 or features['avg_word_length'] < 3:
                inconsistencies.append(f"Unusual average word length: {features['avg_word_length']:.2f}")
            
            if inconsistencies:
                stylometric_suspicions.append({
                    'script_id': script['id'],
                    'filename': script['filename'],
                    'inconsistencies': inconsistencies,
                    'features': features,
                    'detection_method': 'stylometric_analysis'
                })
        
        return stylometric_suspicions
    
    def calculate_text_similarity(self):
        """Calculate cosine similarity between all script pairs"""
        if len(self.answer_scripts) < 2:
            return []
            
        texts = [script['cleaned_text'] for script in self.answer_scripts]
        
        # Filter out empty texts
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and len(text.strip()) > 10:  # Only texts with substantial content
                valid_texts.append(text)
                valid_indices.append(i)
        
        if len(valid_texts) < 2:
            return []
        
        try:
            vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
            tfidf_matrix = vectorizer.fit_transform(valid_texts)
            
            similarity_matrix = cosine_similarity(tfidf_matrix)
            high_similarity_pairs = []
            
            for idx_i, i in enumerate(valid_indices):
                for idx_j, j in enumerate(valid_indices):
                    if idx_i >= idx_j:  # Avoid duplicate comparisons and self-comparison
                        continue
                        
                    similarity_score = similarity_matrix[idx_i][idx_j]
                    
                    # Adjust threshold based on text length and content
                    script1 = self.answer_scripts[i]
                    script2 = self.answer_scripts[j]
                    
                    # Only consider substantial similarities
                    if similarity_score > 0.6:  # Lowered threshold for demo
                        # Find suspicious lines
                        suspicious_lines = self.find_suspicious_lines(
                            script1['raw_text'], 
                            script2['raw_text']
                        )
                        
                        # Generate recommendation
                        recommendation = self.generate_recommendation(similarity_score, len(suspicious_lines))
                        
                        high_similarity_pairs.append({
                            'script1_id': script1['id'],
                            'script2_id': script2['id'],
                            'script1_file': script1['filename'],
                            'script2_file': script2['filename'],
                            'similarity_score': similarity_score,
                            'suspicious_lines': suspicious_lines,
                            'recommendation': recommendation,
                            'detection_method': 'text_similarity'
                        })
            
            return high_similarity_pairs
            
        except Exception as e:
            print(f"Error in text similarity calculation: {e}")
            return []
    
    def find_suspicious_lines(self, text1, text2, similarity_threshold=0.8):
        """Find specific suspicious lines between two texts"""
        lines1 = [line.strip() for line in text1.split('\n') if line.strip()]
        lines2 = [line.strip() for line in text2.split('\n') if line.strip()]
        
        suspicious_pairs = []
        
        for i, line1 in enumerate(lines1):
            for j, line2 in enumerate(lines2):
                if len(line1) > 20 and len(line2) > 20:  # Only substantial lines
                    similarity = self.calculate_line_similarity(line1, line2)
                    if similarity > similarity_threshold:
                        suspicious_pairs.append({
                            'line_number_script1': i + 1,
                            'line_number_script2': j + 1,
                            'text_script1': line1[:100] + "..." if len(line1) > 100 else line1,
                            'text_script2': line2[:100] + "..." if len(line2) > 100 else line2,
                            'similarity': similarity
                        })
        
        return suspicious_pairs[:10]  # Return top 10 most suspicious pairs
    
    def calculate_line_similarity(self, line1, line2):
        """Calculate similarity between two lines using multiple methods"""
        # Method 1: Cosine similarity with TF-IDF
        vectorizer = TfidfVectorizer().fit_transform([line1, line2])
        vectors = vectorizer.toarray()
        cosine_sim = cosine_similarity(vectors[0:1], vectors[1:2])[0][0]
        
        # Method 2: Sequence matcher (character-based)
        sequence_sim = SequenceMatcher(None, line1, line2).ratio()
        
        # Combine both methods
        combined_similarity = (cosine_sim + sequence_sim) / 2
        
        return combined_similarity
    
    def generate_recommendation(self, similarity_score, num_suspicious_lines):
        """Generate recommendation based on analysis results"""
        if similarity_score > 0.9 and num_suspicious_lines > 5:
            return "🚨 HIGH RISK: Strong evidence of copying. Multiple suspicious lines detected. Immediate investigation recommended."
        elif similarity_score > 0.8 and num_suspicious_lines > 3:
            return "⚠️ MEDIUM-HIGH RISK: Significant similarities with multiple matching lines. Detailed review required."
        elif similarity_score > 0.7:
            return "⚠️ MEDIUM RISK: Notable similarities detected. Further investigation recommended."
        elif similarity_score > 0.6:
            return "📝 LOW-MEDIUM RISK: Some similarities found. Monitor for future assignments."
        elif similarity_score > 0.5:
            return "📝 LOW RISK: Minor similarities detected. Normal academic variations."
        else:
            return "✅ MINIMAL RISK: Normal variations detected. No significant concerns."
    
    def generate_comprehensive_report(self):
        """Generate a comprehensive dishonesty detection report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_scripts_processed': len(self.answer_scripts),
            'detection_results': {}
        }
        
        # Run all detection methods
        report['detection_results']['identical_wrong_answers'] = self.detect_identical_wrong_answers()
        report['detection_results']['rare_answer_patterns'] = self.detect_rare_answer_patterns()
        report['detection_results']['stylometric_analysis'] = self.perform_stylometric_analysis()
        report['detection_results']['text_similarity'] = self.calculate_text_similarity()
        
        # Calculate risk scores for each script
        report['script_risk_scores'] = self.calculate_risk_scores(report)
        
        # Generate overall assessment
        report['overall_assessment'] = self.generate_overall_assessment(report)
        
        return report
    
    def calculate_risk_scores(self, report):
        """Calculate risk scores for each script based on all detection methods"""
        risk_scores = defaultdict(lambda: {'score': 0, 'reasons': [], 'risk_level': 'LOW'})
        
        # Score identical wrong answers
        for pair in report['detection_results']['identical_wrong_answers']:
            risk_scores[pair['script1_id']]['score'] += pair['similarity_score'] * 100
            risk_scores[pair['script1_id']]['reasons'].append(f"Identical wrong answers with script {pair['script2_id']} (Score: {pair['similarity_score']:.2f})")
            
            risk_scores[pair['script2_id']]['score'] += pair['similarity_score'] * 100
            risk_scores[pair['script2_id']]['reasons'].append(f"Identical wrong answers with script {pair['script1_id']} (Score: {pair['similarity_score']:.2f})")
        
        # Score rare answer patterns
        for rare in report['detection_results']['rare_answer_patterns']:
            risk_score = len(rare['rare_answers']) * 15
            risk_scores[rare['script_id']]['score'] += risk_score
            risk_scores[rare['script_id']]['reasons'].append(f"Rare answer patterns: {len(rare['rare_answers'])} instances")
        
        # Score stylometric inconsistencies
        for stylo in report['detection_results']['stylometric_analysis']:
            risk_scores[stylo['script_id']]['score'] += len(stylo['inconsistencies']) * 20
            risk_scores[stylo['script_id']]['reasons'].append(f"Stylometric inconsistencies: {len(stylo['inconsistencies'])} issues")
        
        # Score text similarity
        for similarity in report['detection_results']['text_similarity']:
            risk_addition = similarity['similarity_score'] * 80
            risk_scores[similarity['script1_id']]['score'] += risk_addition
            risk_scores[similarity['script1_id']]['reasons'].append(f"High text similarity ({similarity['similarity_score']:.2f}) with script {similarity['script2_id']}")
            
            risk_scores[similarity['script2_id']]['score'] += risk_addition
            risk_scores[similarity['script2_id']]['reasons'].append(f"High text similarity ({similarity['similarity_score']:.2f}) with script {similarity['script1_id']}")
        
        # Determine risk levels
        for script_id in risk_scores:
            score = risk_scores[script_id]['score']
            if score > 100:
                risk_scores[script_id]['risk_level'] = 'VERY HIGH'
            elif score > 70:
                risk_scores[script_id]['risk_level'] = 'HIGH'
            elif score > 40:
                risk_scores[script_id]['risk_level'] = 'MEDIUM'
            elif score > 20:
                risk_scores[script_id]['risk_level'] = 'LOW'
            else:
                risk_scores[script_id]['risk_level'] = 'VERY LOW'
        
        return dict(risk_scores)
    
    def generate_overall_assessment(self, report):
        """Generate overall assessment of the analysis"""
        total_scripts = len(self.answer_scripts)
        high_risk_count = sum(1 for score in report['script_risk_scores'].values() 
                            if score['risk_level'] in ['HIGH', 'VERY HIGH'])
        
        if high_risk_count == 0:
            return {
                'assessment': 'CLEAN',
                'message': 'No significant academic dishonesty detected. All scripts show normal variations.',
                'confidence': 'HIGH'
            }
        elif high_risk_count / total_scripts < 0.2:
            return {
                'assessment': 'MINOR CONCERNS',
                'message': f'Minor concerns detected in {high_risk_count} out of {total_scripts} scripts. Routine monitoring recommended.',
                'confidence': 'MEDIUM'
            }
        elif high_risk_count / total_scripts < 0.5:
            return {
                'assessment': 'SIGNIFICANT CONCERNS',
                'message': f'Significant concerns detected in {high_risk_count} out of {total_scripts} scripts. Detailed investigation recommended.',
                'confidence': 'HIGH'
            }
        else:
            return {
                'assessment': 'MAJOR CONCERNS',
                'message': f'Major concerns detected in {high_risk_count} out of {total_scripts} scripts. Immediate action required.',
                'confidence': 'HIGH'
            }
    
    # Helper methods
    def clean_text(self, text):
        """Clean and normalize text"""
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\.\,\?\!]', '', text)
        
        return text.lower()  # Convert to lowercase for consistency
    
    def extract_answers(self, text):
        """Extract answers from text with multiple pattern matching"""
        answers = {}
        
        # Multiple patterns for question detection
        patterns = [
            r'(?:Q|Question)[\s\.]*(\d+)[\s\.]*[:\)\-]\s*([^\nQ]+)',
            r'(?:Q|Question)[\s\.]*(\d+)[\s\.]*[:\)\-]\s*([^\n]+?)(?=(?:Q|Question|\n\n|$))',
            r'(\d+)[\s\.]*[\)\.]\s*([^\n\d]+?)(?=(?:\d+[\)\.]|\n\n|$))'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                question_num, answer = match
                clean_answer = answer.strip()
                if len(clean_answer) > 3:  # Only substantial answers
                    answers[question_num.strip()] = clean_answer
        
        return answers
    
    def find_common_wrong_answers(self, answers1, answers2):
        """Find identical wrong answers between two scripts"""
        common_wrong = []
        
        for q_num in set(answers1.keys()) & set(answers2.keys()):
            answer1 = answers1[q_num]
            answer2 = answers2[q_num]
            
            if (answer1 == answer2 and 
                answer1.strip() and  # Not empty
                len(answer1) > 3 and  # Substantial answer
                not self.is_common_answer(answer1)):  # Not a common expected answer
                common_wrong.append({
                    'question': q_num,
                    'answer': answer1,
                    'similarity': 1.0
                })
        
        return common_wrong
    
    def is_common_answer(self, answer):
        """Check if answer is a common expected answer"""
        common_responses = ['yes', 'no', 'true', 'false', 'maybe', 'perhaps', 'sometimes']
        return answer.lower().strip() in common_responses or len(answer) < 5
    
    def extract_stylometric_features(self, text):
        """Extract comprehensive writing style features"""
        sentences = re.split(r'[.!?]+', text)
        words = re.findall(r'\b\w+\b', text.lower())
        characters = re.findall(r'[a-zA-Z]', text)
        
        if len(sentences) == 0 or len(words) == 0:
            return {
                'avg_sentence_length': 0,
                'vocabulary_richness': 0,
                'punctuation_density': 0,
                'avg_word_length': 0,
                'word_count': 0,
                'sentence_count': 0,
                'character_count': len(text)
            }
        
        unique_words = set(words)
        punctuation_count = len(re.findall(r'[^\w\s]', text))
        
        # Calculate average word length
        total_word_chars = sum(len(word) for word in words)
        avg_word_length = total_word_chars / len(words) if words else 0
        
        return {
            'avg_sentence_length': len(words) / len(sentences),
            'vocabulary_richness': len(unique_words) / len(words) if words else 0,
            'punctuation_density': punctuation_count / len(text) if text else 0,
            'avg_word_length': avg_word_length,
            'word_count': len(words),
            'sentence_count': len(sentences),
            'character_count': len(text),
            'unique_word_count': len(unique_words)
        }
    
    def generate_text_hash(self, text):
        """Generate hash for text comparison"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def ocr_space_file(self, filename, overlay=False, api_key='helloworld', language='eng',
                      is_table=False, OCREngine=2, detect_orientation=True, scale=True,
                      is_create_searchable_pdf=True, is_searchable_pdf_hidden=False):
        """OCR.space API request with local file. Returns JSON as Python dict."""
        payload = {
            'isOverlayRequired': overlay,
            'apikey': api_key,
            'language': language,
            'isTable': is_table,
            'OCREngine': OCREngine,
            'detectOrientation': detect_orientation,
            'scale': scale,
            'isCreateSearchablePdf': is_create_searchable_pdf,
            'isSearchablePdfHideTextLayer': is_searchable_pdf_hidden,
        }

        max_retries = 3
        retry_delay = 2
        timeout = 120  # Increased timeout to 120 seconds

        import time

        for attempt in range(max_retries):
            try:
                with open(filename, 'rb') as f:
                    # Check file size again before sending
                    file_size = os.path.getsize(filename)
                    if file_size > 1024 * 1024:  # 1MB in bytes
                        print(f"⚠️ Warning: File {filename} is still too large ({file_size/1024/1024:.2f} MB) after compression")
                    
                    r = requests.post(
                        'https://api.ocr.space/parse/image',
                        files={'file': f},
                        data=payload,
                        timeout=timeout
                    )
                
                return r.json()
            except requests.exceptions.Timeout:
                print(f"Timeout error on attempt {attempt + 1}/{max_retries}. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            except requests.exceptions.RequestException as e:
                print(f"Request error on attempt {attempt + 1}/{max_retries}: {str(e)}")
                if attempt == max_retries - 1:
                    return {"ErrorMessage": f"Request failed after {max_retries} attempts: {str(e)}"}
                time.sleep(retry_delay)
            except Exception as e:
                return {"ErrorMessage": f"Unexpected error: {str(e)}"}
        
        return {"ErrorMessage": "Request failed: Max retries exceeded"}

    def extract_text(self, result):
        """Safely extract parsed text or show error"""
        if isinstance(result, dict) and "ParsedResults" in result:
            parsed_results = result["ParsedResults"]
            if parsed_results and isinstance(parsed_results, list):
                # Check for error messages in the parsed results
                error_message = parsed_results[0].get("ErrorMessage", "")
                if error_message:
                    return f"Error: {error_message}"
                return parsed_results[0].get("ParsedText", "").strip()
            else:
                return "Error: No parsed results in response"
        elif isinstance(result, dict) and "ErrorMessage" in result:
            return f"Error: {result.get('ErrorMessage', 'Unknown error')}"
        else:
            return "Error: Unexpected response format"

# Utility function for batch processing
def process_student_data(student_data, file_mapping, api_key):
    """Process student data with file mappings"""
    detector = AcademicDishonestyDetector()
    
    # Prepare file paths
    file_paths = []
    student_info = []
    
    for student in student_data:
        filename = file_mapping.get(student['exam_number'])
        if filename and os.path.exists(filename):
            file_paths.append(filename)
            student_info.append({
                'student_id': student['id'],
                'name': student['name'],
                'reg_number': student['reg_number'],
                'exam_number': student['exam_number'],
                'file_path': filename
            })
    
    # Process scripts
    processed_scripts = detector.process_scripts_with_ocr(file_paths, api_key)
    
    # Map processed scripts back to student info
    for i, script in enumerate(processed_scripts):
        if i < len(student_info):
            script['student_info'] = student_info[i]
    
    return detector, processed_scripts

if __name__ == "__main__":
    # Example usage
    detector = AcademicDishonestyDetector()
    
    # Test with sample files (replace with actual file paths)
    sample_files = ["sample1.pdf", "sample2.jpg"]  # Add your file paths here
    
    if all(os.path.exists(f) for f in sample_files):
        processed = detector.process_scripts_with_ocr(sample_files, "K82241565188957")
        report = detector.generate_comprehensive_report()
        
        print("Analysis Complete!")
        print(f"Processed {len(processed)} scripts")
        print(f"Found {len(report['detection_results']['text_similarity'])} suspicious pairs")
    else:
        print("Sample files not found. Please add actual file paths for testing.")