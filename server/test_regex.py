import re

text = """<update>
<update_analysis>
content here
</update_analysis>
_.set('test', 'value');
</update>"""

# Test with raw string pattern
pattern = r'<update>[\s\S]*</update>'
result = re.sub(pattern, '', text, flags=re.DOTALL)
print(f'Input len: {len(text)}, Output len: {len(result)}')
print('Result:', repr(result))

# Test with 's' flag (DOTALL) using .* instead
pattern2 = r'<update>.*</update>'
result2 = re.sub(pattern2, '', text, flags=re.DOTALL)
print(f'With .* and DOTALL: {len(result2)}')
print('Result2:', repr(result2))
