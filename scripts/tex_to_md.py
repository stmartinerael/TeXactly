#!/usr/bin/env python3
import sys
import re

def convert_tex_to_md(tex_content):
    content = tex_content
    
    # 1. Remove form feeds and other control characters
    content = content.replace('\f', '')
    
    # 2. Handle multi-line \def and \outer\def blocks (rough heuristic)
    # We look for \def...{ and try to find the matching closing brace.
    # But a simpler way is to just remove lines between \def and a lone }
    content = re.sub(r'(?m)^\\(def|outer|font|let|catcode|gdef|input|parskip|verbatimdefs|verbatimgobble|begingroup|endgroup|dospecials|matrix|lpile|mainfont|runninghead).*$', '', content)
    
    # 3. Handle comments (remove or convert to MD comments)
    content = re.sub(r'(?<!\\)%.*', '', content)
    
    # 4. Handle basic formatting macros
    content = content.replace(r'\PASCAL', 'Pascal')
    content = content.replace(r'\RA', '→')
    content = content.replace(r'\WEB', 'WEB')
    content = content.replace(r'\TeX', 'TeX')
    content = content.replace(r'\quad', ' ')
    content = content.replace(r'\hfill', '')
    content = content.replace(r'\break', '\n')
    content = content.replace(r'\noindent', '')
    content = content.replace(r'\ignorespaces', '')
    
    # 5. Handle \section #1.
    content = re.sub(r'\\section\s+([^.]+)\.', r'\n## \1\n', content)
    
    # 6. Handle nested font macros (multiple passes)
    for _ in range(3):
        content = re.sub(r'{\\(tt|tentt|titlefont|ttitlefont|sc|sl|it|bf)\s+([^}]+)}', 
                         lambda m: f"`{m.group(2)}`" if m.group(1) in ('tt', 'tentt', 'titlefont', 'ttitlefont') else 
                                   f"*{m.group(2)}*" if m.group(1) in ('sl', 'it', 'sc') else 
                                   f"**{m.group(2)}**", content)
    
    # 7. Handle \.{...} -> `...`
    content = re.sub(r'\\\.{([^}]+)}', r'`\1`', content)
    
    # 8. Handle \centerline{...} (handling one level of nesting)
    content = re.sub(r'\\centerline{([^{}]*({[^{}]*}[^{}]*)*)}', r'\n<p align="center">\1</p>\n', content)
    
    # 9. Remove remaining low-level TeX commands
    content = re.sub(r'\\(vskip|penalty|hsize|vsize|pageno|vfill|eject|mainfont)[^ \n{]*', '', content)
    
    # 10. Handle literal braces \{ and \}
    content = content.replace(r'\{', '{').replace(r'\}', '}')
    
    # 11. Cleanup multiple newlines and spaces
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r' +', ' ', content)
    
    return content.strip()

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.tex> <output.md>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(input_file, 'r', encoding='latin-1') as f:
            tex_content = f.read()
        
        md_content = convert_tex_to_md(tex_content)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"Successfully converted {input_file} to {output_file}")
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
