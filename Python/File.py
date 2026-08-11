import os
import sys
import hashlib
import datetime
import shutil
from PIL import Image
from PIL.ExifTags import TAGS
import PyPDF2
import argparse
import json
import csv
import re
import subprocess

def extract_metadata_image(file_path):
    metadata = {}
    try:
        img = Image.open(file_path)
        metadata['format'] = img.format
        metadata['mode'] = img.mode
        metadata['size'] = img.size
        info = img.info
        if 'dpi' in info:
            metadata['dpi'] = info['dpi']
        exif = img._getexif()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                metadata[tag] = str(value)
    except Exception as e:
        metadata['error'] = str(e)
    return metadata

def extract_metadata_pdf(file_path):
    metadata = {}
    try:
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            info = pdf.metadata
            if info:
                for key, value in info.items():
                    metadata[key] = value
            metadata['pages'] = len(pdf.pages)
    except Exception as e:
        metadata['error'] = str(e)
    return metadata

def calculate_hashes(file_path):
    hashes = {}
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
            hashes['md5'] = hashlib.md5(data).hexdigest()
            hashes['sha1'] = hashlib.sha1(data).hexdigest()
            hashes['sha256'] = hashlib.sha256(data).hexdigest()
    except Exception as e:
        hashes['error'] = str(e)
    return hashes

def extract_strings(file_path, min_length=6):
    strings = []
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
            pattern = re.compile(b'[\\x20-\\x7E]{' + str(min_length).encode() + b',}')
            matches = pattern.findall(data)
            for match in matches:
                try:
                    decoded = match.decode('utf-8', errors='ignore')
                    strings.append(decoded)
                except:
                    pass
    except Exception as e:
        strings.append(f"Error: {str(e)}")
    return strings

def extract_embedded_objects(file_path):
    objects = []
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        patterns = [
            (b'%PDF', 'PDF Header'),
            (b'JFIF', 'JPEG Marker'),
            (b'PNG', 'PNG Signature'),
            (b'GIF8', 'GIF Signature'),
            (b'PK\\x03\\x04', 'ZIP Archive'),
        ]
        for pattern, obj_type in patterns:
            if pattern in data:
                objects.append(obj_type)
    except Exception as e:
        objects.append(f"Error: {str(e)}")
    return objects

def compare_files(file1, file2):
    comparison = {}
    try:
        hash1 = calculate_hashes(file1)
        hash2 = calculate_hashes(file2)
        comparison['hash_match'] = hash1.get('md5') == hash2.get('md5')
        comparison['size_match'] = os.path.getsize(file1) == os.path.getsize(file2)
        comparison['name_match'] = os.path.basename(file1) == os.path.basename(file2)
        comparison['file1_hash'] = hash1
        comparison['file2_hash'] = hash2
    except Exception as e:
        comparison['error'] = str(e)
    return comparison

def carve_embedded_files(file_path, output_dir):
    carved = []
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(file_path, 'rb') as f:
            data = f.read()
        markers = [
            (b'\\xff\\xd8\\xff', 'jpg', 'JPEG'),
            (b'\\x89PNG\\r\\n\\x1a\\n', 'png', 'PNG'),
            (b'%PDF', 'pdf', 'PDF'),
        ]
        for marker, ext, file_type in markers:
            positions = []
            start = 0
            while True:
                pos = data.find(marker, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + 1
            for idx, pos in enumerate(positions):
                output_file = os.path.join(output_dir, f"carved_{file_type}_{idx}.{ext}")
                try:
                    end = data.find(b'\\xff\\xd9', pos)
                    if end != -1:
                        with open(output_file, 'wb') as out:
                            out.write(data[pos:end+2])
                        carved.append(output_file)
                except:
                    continue
    except Exception as e:
        carved.append(f"Error: {str(e)}")
    return carved

def analyze_forensics(file_path, output_format='json'):
    results = {}
    results['file'] = file_path
    results['basename'] = os.path.basename(file_path)
    results['size'] = os.path.getsize(file_path)
    results['modified'] = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
    results['created'] = datetime.datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
    results['accessed'] = datetime.datetime.fromtimestamp(os.path.getatime(file_path)).isoformat()
    results['hashes'] = calculate_hashes(file_path)
    results['strings'] = extract_strings(file_path)
    results['embedded_objects'] = extract_embedded_objects(file_path)
    ext = os.path.splitext(file_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
        results['metadata'] = extract_metadata_image(file_path)
    elif ext == '.pdf':
        results['metadata'] = extract_metadata_pdf(file_path)
    else:
        results['metadata'] = {'warning': 'No specific metadata parser'}
    return results

def export_report(data, output_file, format_type='json'):
    if format_type == 'json':
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    elif format_type == 'csv':
        flat_data = []
        def flatten_dict(d, prefix=''):
            for key, value in d.items():
                if isinstance(value, dict):
                    flatten_dict(value, f"{prefix}{key}.")
                elif isinstance(value, list):
                    flat_data.append({f"{prefix}{key}": str(value)})
                else:
                    flat_data.append({f"{prefix}{key}": str(value)})
        flatten_dict(data)
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=flat_data[0].keys() if flat_data else [])
            writer.writeheader()
            writer.writerows(flat_data)
    elif format_type == 'txt':
        with open(output_file, 'w') as f:
            def write_dict(d, indent=0):
                for key, value in d.items():
                    f.write('  ' * indent + f"{key}: ")
                    if isinstance(value, dict):
                        f.write('\n')
                        write_dict(value, indent+1)
                    elif isinstance(value, list):
                        f.write('\n')
                        for item in value:
                            f.write('  ' * (indent+1) + f"- {item}\n")
                    else:
                        f.write(f"{value}\n")
            write_dict(data)
    return output_file

def batch_process(directory, output_dir, file_types=None):
    if file_types is None:
        file_types = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.pdf', '.docx', '.xlsx']
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in file_types:
                file_path = os.path.join(root, file)
                try:
                    result = analyze_forensics(file_path)
                    rel_path = os.path.relpath(file_path, directory)
                    results[rel_path] = result
                except Exception as e:
                    results[file] = {'error': str(e)}
    report_file = os.path.join(output_dir, 'batch_report.json')
    export_report(results, report_file, 'json')
    return results

def find_duplicates(directory):
    hashes = {}
    duplicates = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                file_hash = calculate_hashes(file_path).get('md5')
                if file_hash:
                    if file_hash in hashes:
                        if file_hash not in duplicates:
                            duplicates[file_hash] = [hashes[file_hash]]
                        duplicates[file_hash].append(file_path)
                    else:
                        hashes[file_hash] = file_path
            except:
                continue
    return {k: v for k, v in duplicates.items() if len(v) > 1}

def generate_timeline(file_paths):
    timeline = []
    for file_path in file_paths:
        try:
            stats = os.stat(file_path)
            timeline.append({
                'file': file_path,
                'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                'accessed': datetime.datetime.fromtimestamp(stats.st_atime).isoformat()
            })
        except:
            continue
    timeline.sort(key=lambda x: x['created'])
    return timeline

def recover_deleted_files(device, output_dir):
    try:
        subprocess.run(['testdisk', '/list'], capture_output=True)
    except FileNotFoundError:
        return "TestDisk not found. Please install testdisk."
    results = []
    try:
        output = subprocess.check_output(['testdisk', '/log', device], stderr=subprocess.STDOUT)
        results.append(f"TestDisk recovery initiated for {device}")
        results.append(f"Output saved to {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        with open(os.path.join(output_dir, 'testdisk_log.txt'), 'wb') as f:
            f.write(output)
        results.append("Check testdisk_log.txt for recovery details")
    except Exception as e:
        results.append(f"Error: {str(e)}")
    return results

def image_forensics(file_path, output_dir):
    results = analyze_forensics(file_path)
    results['carved_files'] = carve_embedded_files(file_path, output_dir)
    return results

def pdf_forensics(file_path, output_dir):
    results = analyze_forensics(file_path)
    try:
        with open(file_path, 'rb') as f:
            pdf = PyPDF2.PdfReader(f)
            results['total_pages'] = len(pdf.pages)
            results['encrypted'] = pdf.is_encrypted
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    results[f'page_{i+1}_text_preview'] = text[:200]
                results[f'page_{i+1}_rotation'] = page.get('/Rotate', 0)
    except Exception as e:
        results['pdf_error'] = str(e)
    results['carved_files'] = carve_embedded_files(file_path, output_dir)
    return results

def main():
    parser = argparse.ArgumentParser(description='Forensic analysis tool for images and PDFs')
    parser.add_argument('file', nargs='?', help='File to analyze')
    parser.add_argument('-b', '--batch', help='Batch process directory')
    parser.add_argument('-o', '--output', default='forensics_output', help='Output directory')
    parser.add_argument('-f', '--format', choices=['json', 'csv', 'txt'], default='json', help='Output format')
    parser.add_argument('-d', '--duplicates', help='Find duplicates in directory')
    parser.add_argument('--timeline', help='Generate timeline for files in directory')
    parser.add_argument('--recover', help='Recover deleted files from device')
    parser.add_argument('--carve', action='store_true', help='Carve embedded files')
    parser.add_argument('--image', action='store_true', help='Image forensic analysis')
    parser.add_argument('--pdf', action='store_true', help='PDF forensic analysis')
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.batch:
        results = batch_process(args.batch, args.output)
        print(f"Batch processing complete. Results in {args.output}/batch_report.json")
    elif args.duplicates:
        results = find_duplicates(args.duplicates)
        report_file = os.path.join(args.output, 'duplicates.json')
        export_report(results, report_file, 'json')
        print(f"Duplicate report saved to {report_file}")
    elif args.timeline:
        files = []
        for root, dirs, filenames in os.walk(args.timeline):
            for f in filenames:
                files.append(os.path.join(root, f))
        timeline = generate_timeline(files)
        report_file = os.path.join(args.output, 'timeline.json')
        export_report(timeline, report_file, 'json')
        print(f"Timeline saved to {report_file}")
    elif args.recover:
        results = recover_deleted_files(args.recover, args.output)
        print("\n".join(results))
    elif args.file:
        if args.image:
            results = image_forensics(args.file, args.output)
        elif args.pdf:
            results = pdf_forensics(args.file, args.output)
        else:
            results = analyze_forensics(args.file)
        if args.carve:
            results['carved_files'] = carve_embedded_files(args.file, args.output)
        output_file = os.path.join(args.output, f"{os.path.splitext(os.path.basename(args.file))[0]}_report.{args.format}")
        export_report(results, output_file, args.format)
        print(f"Report saved to {output_file}")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()