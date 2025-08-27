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
                inline = tokens[i + 1]
                text = self._collect_text(inline)
                blocks.append({"type": "header", "data": {"text": text, "level": level}})
                i += 3
                continue

            # Paragraph
            elif token.type == "paragraph_open":
                inline = tokens[i + 1]
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
                        text_lines.append(self._collect_text(tokens[j + 1]))
                        j += 3
                    else:
                        j += 1
                blocks.append({
                    "type": "quote",
                    "data": {"text": "\n".join(text_lines), "caption": "", "alignment": "left"}
                })
                i = j + 1
                continue

            # Lists (ordered, unordered, nested)
            elif token.type in ("bullet_list_open", "ordered_list_open"):
                list_block, new_i = self._parse_list(tokens, i)
                blocks.append(list_block)
                i = new_i
                continue

            i += 1

        return {"time": int(time.time() * 1000), "blocks": blocks, "version": "2.29.1"}

    def _parse_list(self, tokens, start_index):
        """
        Recursively parse a list block including nested lists and multi-paragraph items.
        """
        token = tokens[start_index]
        style = "unordered" if token.type == "bullet_list_open" else "ordered"
        items = []
        i = start_index + 1

        while i < len(tokens) and tokens[i].type != token.type.replace("_open", "_close"):
            if tokens[i].type == "list_item_open":
                j = i + 1
                item_lines = []
                while j < len(tokens) and tokens[j].type != "list_item_close":
                    t = tokens[j]
                    if t.type == "paragraph_open":
                        item_lines.append(self._collect_text(tokens[j + 1]))
                        j += 3  # skip paragraph_open, inline, paragraph_close
                    elif t.type in ("bullet_list_open", "ordered_list_open"):
                        # nested list
                        nested_block, new_j = self._parse_list(tokens, j)
                        nested_list_str = json.dumps(nested_block["data"])
                        item_lines.append(nested_list_str)
                        j = new_j
                    elif t.type == "inline":
                        item_lines.append(self._collect_text(t))
                        j += 1
                    else:
                        j += 1
                items.append("\n".join(item_lines))
                i = j + 1
            else:
                i += 1

        return {"type": "list", "data": {"style": style, "items": items}}, i

    def _collect_text(self, token):
        """
        Recursively collect text from inline tokens.
        Handles bold (**), italic (*), bold+italic (***), inline code, links, and html_inline.
        """
        if token.type != "inline":
            return getattr(token, "content", "")

        result = ""
        i = 0
        children = token.children or []
        while i < len(children):
            c = children[i]

            # Text
            if c.type == "text":
                result += getattr(c, "content", "")

            # Bold + Italic (***) or bold (**) or italic (*)
            elif c.type == "strong_open":
                # Check if next is em_open (bold+italic)
                if i + 1 < len(children) and children[i + 1].type == "em_open":
                    # bold+italic
                    inner = ""
                    j = i + 2
                    while j < len(children) and children[j].type != "em_close":
                        inner += self._collect_text(children[j])
                        j += 1
                    result += f"<b><i>{inner}</i></b>"
                    # skip strong_close after em_close
                    while j < len(children) and children[j].type != "strong_close":
                        j += 1
                    i = j
                else:
                    # bold only
                    inner = ""
                    j = i + 1
                    while j < len(children) and children[j].type != "strong_close":
                        inner += self._collect_text(children[j])
                        j += 1
                    result += f"<b>{inner}</b>"
                    i = j

            elif c.type == "em_open":
                # italic only
                inner = ""
                j = i + 1
                while j < len(children) and children[j].type != "em_close":
                    inner += self._collect_text(children[j])
                    j += 1
                result += f"<i>{inner}</i>"
                i = j

            # Inline code
            elif c.type == "code_inline":
                result += f"<code>{getattr(c, 'content', '')}</code>"

            # HTML inline
            elif c.type == "html_inline":
                result += getattr(c, "content", "")

            # Other inline children
            elif hasattr(c, "children") and c.children:
                result += self._collect_text(c)

            i += 1

        return result


if __name__ == "__main__":
    md_text = """# Heading

1. First item
2. Second item with **bold** and *italic* and ***bold+italic***
   - Nested item a
   - Nested item b
3. Third item
   Another paragraph inside third item
4. Fourth item
"""
    converter = MarkdownToEditorJS()
    print(json.dumps(converter.convert(md_text), indent=2))
