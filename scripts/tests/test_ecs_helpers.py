import os
import sys
import unittest

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from scripts.generators import ecs_helpers


class TestECSHelpers(unittest.TestCase):
    # dict_copy_existing_keys

    def test_dict_copy_existing_keys(self):
        source = {'key1': 'value1'}
        destination = {}
        ecs_helpers.dict_copy_existing_keys(source, destination, ['key1', 'missingkey'])
        self.assertEqual(destination, {'key1': 'value1'})

    def test_dict_copy_existing_keys_overwrites(self):
        source = {'key1': 'new_value'}
        destination = {'key1': 'overwritten', 'untouched': 'untouched'}
        ecs_helpers.dict_copy_existing_keys(source, destination, ['key1', 'untouched'])
        self.assertEqual(destination, {'key1': 'new_value', 'untouched': 'untouched'})

    # dict_sorted_by_keys

    def test_sorted_by_one_key(self):
        dict = {
            'message': {'name': 'message'},
            'labels': {'name': 'labels'},
            '@timestamp': {'name': '@timestamp'},
            'tags': {'name': 'tags'}
        }
        expected = [
            {'name': '@timestamp'},
            {'name': 'labels'},
            {'name': 'message'},
            {'name': 'tags'}
        ]
        result = ecs_helpers.dict_sorted_by_keys(dict, 'name')
        self.assertEqual(result, expected)
        result = ecs_helpers.dict_sorted_by_keys(dict, ['name'])
        self.assertEqual(result, expected)

    def test_sorted_by_multiple_keys(self):
        dict = {
            'cloud': {'group': 2, 'name': 'cloud'},
            'agent': {'group': 2, 'name': 'agent'},
            'base': {'group': 1, 'name': 'base'},
        }
        expected = [
            {'group': 1, 'name': 'base'},
            {'group': 2, 'name': 'agent'},
            {'group': 2, 'name': 'cloud'}
        ]
        result = ecs_helpers.dict_sorted_by_keys(dict, ['group', 'name'])
        self.assertEqual(result, expected)

    def test_merge_dicts(self):
        a = {
            'cloud': {'group': 2, 'name': 'cloud'},
            'agent': {'group': 2, 'name': 'agent'},
        }
        b = {'base': {'group': 1, 'name': 'base'}}

        result = ecs_helpers.safe_merge_dicts(a, b)

        self.assertEqual(result,
                         {
                             'cloud': {'group': 2, 'name': 'cloud'},
                             'agent': {'group': 2, 'name': 'agent'},
                             'base': {'group': 1, 'name': 'base'}
                         })

    def test_merge_dicts_raises_if_duplicate_key_added(self):
        a = {'cloud': {'group': 2, 'name': 'cloud'}}
        b = {'cloud': {'group': 9, 'name': 'bazbar'}}

        with self.assertRaises(ValueError):
            ecs_helpers.safe_merge_dicts(a, b)

    def test_clean_string_values(self):
        dict = {'dirty': ' space, the final frontier  ', 'clean': 'val', 'int': 1}
        ecs_helpers.dict_clean_string_values(dict)
        self.assertEqual(dict, {'dirty': 'space, the final frontier', 'clean': 'val', 'int': 1})

    def test_list_slit_by(self):
        lst = ['ecs', 'has', 'a', 'meme', 'now']
        split_list = ecs_helpers.list_split_by(lst, 3)
        self.assertEqual(split_list, [['ecs', 'has', 'a'], ['meme', 'now']])

    def test_recursive_subset_merge(self):
        subset_a = {
            'field1': {
                'fields': {
                    'subfield1': {
                        'fields': {
                            'subsubfield1': {
                                'fields': '*'
                            }
                        }
                    },
                    'subfield2': {
                        'fields': '*'
                    }
                }
            },
            'field2': {}
        }
        subset_b = {
            'field1': {
                'fields': {
                    'subfield1': {
                        'fields': '*'
                    },
                    'subfield3': {
                        'fields': '*'
                    }
                }
            },
            'field2': {
                'fields': {
                    'subfield2': {
                        'fields': '*'
                    }
                }
            },
            'field3': {
                'fields': '*'
            }
        }
        expected = {
            'field1': {
                'fields': {
                    'subfield1': {
                        'fields': '*'
                    },
                    'subfield2': {
                        'fields': '*'
                    },
                    'subfield3': {
                        'fields': '*'
                    }
                }
            },
            'field2': {
                'fields': '*'
            },
            'field3': {
                'fields': '*'
            }
        }
        ecs_helpers.recursive_merge_subset_dicts(subset_a, subset_b)
        self.assertEqual(subset_a, expected)

    def test_fields_subset(self):
        fields = {
            'test_fieldset': {
                'name': 'test_fieldset',
                'fields': {
                    'test_field1': {
                        'field_details': {
                            'name': 'test_field1',
                            'type': 'keyword',
                            'description': 'A test field'
                        }
                    },
                    'test_field2': {
                        'field_details': {
                            'name': 'test_field2',
                            'type': 'keyword',
                            'description': 'Another test field'
                        }
                    }
                }
            }
        }
        subset = {
            'test_fieldset': {
                'fields': {
                    'test_field1': {
                        'fields': '*'
                    }
                }
            }
        }
        expected = {
            'test_fieldset': {
                'name': 'test_fieldset',
                'fields': {
                    'test_field1': {
                        'field_details': {
                            'name': 'test_field1',
                            'type': 'keyword',
                            'description': 'A test field'
                        }
                    }
                }
            }
        }
        actual = ecs_helpers.fields_subset(subset, fields)
        self.assertEqual(actual, expected)

    def test_get_nested_field(self):
        fields = {
            'test_fieldset': {
                'name': 'test_fieldset',
                'fields': {
                    'test_field1': {
                        'field_details': {
                            'name': 'test_field1',
                            'type': 'keyword',
                            'description': 'A test field'
                        }
                    },
                    'test_field2': {
                        'field_details': {
                            'name': 'test_field2',
                            'type': 'keyword',
                            'description': 'Another test field'
                        }
                    }
                }
            }
        }
        nested_field_name = 'test_fieldset.test_field1'
        expected = {
            'field_details': {
                'name': 'test_field1',
                'type': 'keyword',
                'description': 'A test field'
            }
        }
        actual = ecs_helpers.get_nested_field(nested_field_name, fields)
        self.assertEqual(actual, expected)

    def test_get_tree_by_ref(self):
        ref = 'v1.5.0'
        tree = ecs_helpers.get_tree_by_ref(ref)
        self.assertEqual(tree.hexsha, '4449df245f6930d59bcd537a5958891261a9476b')


if __name__ == '__main__':
    unittest.main()
