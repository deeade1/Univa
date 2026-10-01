
def clean_editor_js(content, to_string=False):
    """
    Clean and sanitize editor.js content.
    Replaces the removed core.utils.editorjs function.
    """
    if not content:
        return content if not to_string else ""
    
    # If content is a dict (editor.js format), extract plain text
    if isinstance(content, dict):
        blocks = content.get('blocks', [])
        text_parts = []
        for block in blocks:
            if block.get('type') == 'paragraph':
                text_parts.append(block.get('data', {}).get('text', ''))
            elif block.get('type') == 'header':
                text_parts.append(block.get('data', {}).get('text', ''))
            elif block.get('type') == 'list':
                items = block.get('data', {}).get('items', [])
                text_parts.extend(items)
        
        if to_string:
            return ' '.join(text_parts)
        return content
    
    return content


def default_clean_editor_js():
    """Return a default empty dict for editor.js fields."""
    return {}
