import json
import os
import re
import shutil
import sys

from bs4 import BeautifulSoup

image_number = 0

def copy_image(path, out_resources_path):
	global image_number
	input_image = os.path.join(os.path.dirname(in_file), path);
	suffix = input_image[input_image.rfind('.'):]
	output_image = os.path.join(out_resources_path, str(image_number) + suffix)
	image_number += 1
	shutil.copy(input_image, output_image)

	return output_image


def replace_image_src_markdown(match, out_resources_path):
	return "{}{{{{ \"{}\" | relative_url }}}}{}".format(match.group(1), copy_image(match.group(2), out_resources_path), match.group(3))


def fix_html_imgs(html, out_resources_path):
	soup = BeautifulSoup(html, 'html.parser')

	for img in soup.findAll('img'):
	    image_path = img['src']
	    output_path = copy_image(image_path, out_resources_path)
	    img['src'] = '/' + output_path

	return str(soup)


def parse_front_matter(lines):
	if len(lines) <= 2:
		return {}

	if not (lines[0] == '---' and lines[-1] == '---'):
		return {}

	retval = {}

	for line in lines[1:-1]:
		(field, value) = line.split(':', 1)
		retval[field.strip()] = value.strip()

	return retval


if len(sys.argv) <= 1:
	print("No input files.")
	exit()

for in_file in sys.argv[1:]:
	with open(in_file, 'r') as input_file:
		notebook = json.load(input_file)

	if len(notebook['cells']) > 0:
		first_cell = notebook['cells'][0]
		if first_cell['cell_type'] == 'raw':
			front_matter = parse_front_matter([x.strip() for x in first_cell['source']])

	if 'title' in front_matter and 'date' in front_matter:
		filename = front_matter['title'].lower().replace(' ', '-')
		out_file = os.path.join('_posts', front_matter['date'] + '-' + filename + '.md')

	out_resources_dirname = os.path.basename(out_file).split('.',1)[0]
	out_resources_path = os.path.join('assets/', out_resources_dirname)

	if not os.path.isdir(out_resources_path):
		os.makedirs(out_resources_path);

	with open(out_file, 'w') as output_file:
		for cell in notebook['cells']:
			if cell['cell_type'] == 'raw':
				output_file.write(''.join(line for line in cell['source']) + '\n')
			elif cell['cell_type'] == 'markdown':
				for line in cell['source']:
					line = re.sub(r'(!\[.+?\]\()(.+)(\))', lambda x: replace_image_src_markdown(x, out_resources_path), line)
					output_file.write(re.sub('\\$(.+?)\\$', '$$\\1$$', line))
			elif cell['cell_type'] == 'code':
				output_file.write('{% highlight python %}\n')
				for line in cell['source']:
					output_file.write(line)
				output_file.write('\n{% endhighlight %}\n\n')
				for output in cell['outputs']:
					data = output['data']
					if 'application/javascript' in data:
						output_file.write('<script type="text/javascript">')
						output_file.write('\n'.join(line for line in data['application/javascript']) + '\n')
						output_file.write('</script>')
					if 'text/html' in data:
						output_file.write('<figure class="highlight">\n')
						output_file.write(fix_html_imgs('\n'.join((line) for line in data['text/html']), out_resources_path) + '\n\n')
						output_file.write('</figure>\n')
					elif 'text/plain' in data:
						output_file.write('{% highlight python %}\n')
						output_file.write(''.join(data['text/plain']) + '\n')
						output_file.write('{% endhighlight %}\n\n')
				

			output_file.write('\n')

		if 'src' in front_matter:
			output_file.write("""\n---\n*This post was automatically converted from [this]({}) Jupyter notebook.*\n\n---\n"""
				.format(front_matter['src']))

	print("Wrote: {}".format(out_file))
