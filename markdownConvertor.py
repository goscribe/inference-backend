import time
import json
from markdown_it import MarkdownIt

class MarkdownToEditorJS:
    def __init__(self):
        self.md = MarkdownIt()

    def convert(self, markdown_text: str):
        tokens = self.md.parse(markdown_text)
        blocks = []
        i = 0

        while i < len(tokens):
            token = tokens[i]

            # Heading
            if token.type == "heading_open":
                level = int(token.tag[1])
                inline = tokens[i+1]
                text = self._collect_text(inline)
                blocks.append({"type": "header", "data": {"text": text, "level": level}})
                i += 3
                continue

            # Paragraph
            elif token.type == "paragraph_open":
                inline = tokens[i+1]
                text = self._collect_text(inline)
                blocks.append({"type": "paragraph", "data": {"text": text}})
                i += 3
                continue

            # Code fence
            elif token.type == "fence":
                blocks.append({"type": "code", "data": {"code": token.content}})
                i += 1
                continue

            # Blockquote
            elif token.type == "blockquote_open":
                j = i + 1
                text_lines = []
                while tokens[j].type != "blockquote_close":
                    if tokens[j].type == "paragraph_open":
                        text_lines.append(self._collect_text(tokens[j+1]))
                        j += 3
                    else:
                        j += 1
                blocks.append({"type": "quote", "data": {"text": "\n".join(text_lines), "caption": "", "alignment": "left"}})
                i = j + 1
                continue

            # Lists
            elif token.type in ("bullet_list_open", "ordered_list_open"):
                style = "unordered" if token.type == "bullet_list_open" else "ordered"
                items = []
                j = i + 1
                while tokens[j].type != token.type.replace("_open","_close"):
                    if tokens[j].type == "list_item_open":
                        items.append(self._collect_text(tokens[j+1]))
                        j += 3
                    else:
                        j += 1
                blocks.append({"type": "list", "data": {"style": style, "items": items}})
                i = j + 1
                continue

            i += 1

        return {"time": int(time.time() * 1000), "blocks": blocks, "version": "2.29.1"}

    def _collect_text(self, token):
        """
        Recursively collect text from inline tokens.
        Handles text, strong, em, inline code, and links.
        """
        if token.type != "inline":
            return getattr(token, "content", "")  # fallback for non-inline tokens
    
        result = ""
        for c in token.children or []:
            if c.type == "text":
                result += getattr(c, "content", "")
            elif c.type == "strong_open" or c.type == "strong_close":
                continue  # delimiters, skip
            elif c.type == "em_open" or c.type == "em_close":
                continue  # delimiters, skip
            elif c.type == "code_inline":
                result += f"<code>{getattr(c, 'content', '')}</code>"
            elif c.type == "link_open" or c.type == "link_close":
                continue  # links handled via href in other token
            elif c.type == "html_inline":
                result += getattr(c, "content", "")
            elif hasattr(c, "children") and c.children:
                result += self._collect_text(c)  # recurse
        return result

    

if __name__ == "__main__":
    ...