import argparse
import glob
import os
import schema_reader
import yaml

from generators import intermediate_files
from generators import csv_generator
from generators import es_template
from generators import beats
from generators import asciidoc_fields
from generators import ecs_helpers


def main():
    args = argument_parser()
    # Get rid of empty include
    if args.include and [''] == args.include:
        args.include.clear()

    if args.ref:
        # Load ECS schemas from a specific git ref
        print('Loading schemas from git ref ' + args.ref)
        tree = ecs_helpers.get_tree_by_ref(args.ref)
        ecs_version = read_version_from_tree(tree)
        ecs_schemas = schema_reader.load_schemas_from_git(tree)
    else:
        # Load the default schemas
        print('Loading default schemas')
        ecs_version = read_version()
        ecs_schemas = schema_reader.load_schemas_from_files()

    print('Running generator. ECS version ' + ecs_version)
    intermediate_fields = schema_reader.create_schema_dicts(ecs_schemas)

    # Maybe load user specified directory of schemas
    if args.include:
        include_glob = ecs_helpers.get_glob_files(args.include, ecs_helpers.YAML_EXT)

        print('Loading user defined schemas: {0}'.format(include_glob))

        custom_schemas = schema_reader.load_schemas_from_files(include_glob)
        intermediate_custom = schema_reader.create_schema_dicts(custom_schemas)
        schema_reader.merge_schema_fields(intermediate_fields, intermediate_custom)

    schema_reader.assemble_reusables(intermediate_fields)

    if args.subset:
        subset = {}
        for arg in args.subset:
            for file in glob.glob(arg):
                with open(file) as f:
                    raw = yaml.safe_load(f.read())
                    ecs_helpers.recursive_merge_subset_dicts(subset, raw)
        if not subset:
            raise ValueError('Subset option specified but no subsets found')
        intermediate_fields = ecs_helpers.fields_subset(subset, intermediate_fields)

    (nested, flat) = schema_reader.generate_nested_flat(intermediate_fields)

    # default location to save files
    out_dir = 'generated'
    docs_dir = 'docs'
    if args.out:
        out_dir = os.path.join(args.out, out_dir)
        docs_dir = os.path.join(args.out, docs_dir)

    ecs_helpers.make_dirs(out_dir)
    ecs_helpers.make_dirs(docs_dir)

    intermediate_files.generate(nested, flat, out_dir)
    if args.intermediate_only:
        exit()

    csv_generator.generate(flat, ecs_version, out_dir)
    es_template.generate(flat, ecs_version, out_dir, args.template_settings, args.mapping_settings)
    beats.generate(nested, ecs_version, out_dir)
    if args.include or args.subset:
        exit()
    asciidoc_fields.generate(intermediate_fields, ecs_version, docs_dir)


def argument_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('--intermediate-only', action='store_true',
                        help='generate intermediary files only')
    parser.add_argument('--include', nargs='+',
                        help='include user specified directory of custom field definitions')
    parser.add_argument('--subset', nargs='+',
                        help='render a subset of the schema')
    parser.add_argument('--out', action='store', help='directory to store the generated files')
    parser.add_argument('--ref', action='store', help='git reference to use when building schemas')
    parser.add_argument('--template-settings', action='store',
                        help='index template settings to use when generating elasticsearch template')
    parser.add_argument('--mapping-settings', action='store',
                        help='mapping settings to use when generating elasticsearch template')
    return parser.parse_args()


def read_version(file='version'):
    with open(file, 'r') as infile:
        return infile.read().rstrip()


def read_version_from_tree(tree):
    return tree['version'].data_stream.read().decode('utf-8').rstrip()


if __name__ == '__main__':
    main()
