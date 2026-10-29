"""Original38 Node programs with explicit, authenticated current39 text inputs.

The historical38 descriptor and programs remain unchanged. Uniform host LF or
CRLF is compared against the real canonical Git blobs reviewed at source52;
physical RAW source identity remains in the runner's independent photographs.
"""
import hashlib
import json
import re

HISTORICAL_MAP = 'tests/ci_web38/node-new38.json'
CURRENT_MAP = 'tests/ci_web39/node-new38-current39.json'
HISTORICAL_SHA256_LF = 'b3a583ab6c704cfb77bd46af0127bdabd07ea36e0a92416c6597401df2f9c04c'
INPUT_COMMIT = '52c97010793865e6e155d928c4ef1eb88b1a0bdc'
SOURCE_SCOPE = 'current39-canonical-Git-LF-inputs-with-unchanged-original38-programs'
API_PATH = 'web/static/js/api.js'
API_SHA256_LF = '1c3b263f359d9b37ede6893134f212879b05615f56f0c143922c3d4c1c2b6f82'
CASES = {'node-product38': 13, 'node-password38': 25}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_text(raw):
    canonical = raw.replace(b'\r\n', b'\n')
    require(b'\r' not in canonical and raw in (canonical, canonical.replace(b'\n', b'\r\n')),
            'Only uniform LF or CRLF text framing is approved')
    return canonical


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw,
                        usedforsecurity=False).hexdigest()


def read_json(raw):
    def unique(pairs):
        value = {}
        for name, item in pairs:
            require(name not in value, 'Duplicate current39 Node descriptor field')
            value[name] = item
        return value
    return json.loads(raw, object_pairs_hook=unique)


def load_mapping(root):
    historical_raw = canonical_text((root / HISTORICAL_MAP).read_bytes())
    require(hashlib.sha256(historical_raw).hexdigest() == HISTORICAL_SHA256_LF,
            'The authenticated historical38 Node descriptor differs')
    historical = read_json(historical_raw)
    mapping = read_json(canonical_text((root / CURRENT_MAP).read_bytes()))
    require(type(mapping) is dict and set(mapping) == {
        'schema', 'source_scope', 'canonical_input_Git_commit', 'original38_mapping',
        'original38_program_pins', 'phases'}, 'The current39 Node descriptor fields differ')
    require(mapping['schema'] == 'current39-inputs-original38-node-programs-v1'
            and mapping['source_scope'] == SOURCE_SCOPE
            and mapping['canonical_input_Git_commit'] == INPUT_COMMIT,
            'The current39 Node source scope differs')
    require(mapping['original38_mapping'] == {
        'path': HISTORICAL_MAP, 'sha256_LF': HISTORICAL_SHA256_LF,
        'git_blob': git_blob(historical_raw)}, 'The historical38 Node authority differs')
    require(type(mapping['phases']) is dict and list(mapping['phases']) == list(historical['phases'])
            and set(mapping['phases']) == set(CASES)
            and type(mapping['original38_program_pins']) is dict
            and set(mapping['original38_program_pins']) == set(CASES),
            'The exact two original38 Node phases are required')
    shared = {}
    for phase, count in CASES.items():
        original, entry = historical['phases'][phase], mapping['phases'][phase]
        require(type(entry) is dict and set(entry) == set(original), 'A current39 Node phase field differs')
        require(all(entry[name] == original[name] for name in original if name != 'input_files')
                and type(entry['cases']) is int and entry['cases'] == count
                and len(entry['expected_cases']) == len(set(entry['expected_cases'])) == count,
                'Original38 program, preloader or exact ordered criteria differ')
        require(type(entry['input_files']) is dict and set(entry['input_files']) == set(original['input_files']),
                'The complete original direct/transitive input set is required')
        for name, pin in entry['input_files'].items():
            expected = API_SHA256_LF if name == API_PATH else original['input_files'][name]['sha256']
            require(type(pin) is dict and set(pin) == {'framing', 'sha256', 'bytes', 'git_blob'}
                    and pin['framing'] == 'uniform_lf' and pin['sha256'] == expected
                    and type(pin['bytes']) is int and pin['bytes'] > 0
                    and type(pin['git_blob']) is str and re.fullmatch('[0-9a-f]{40}', pin['git_blob']) is not None,
                    'A reviewed canonical current39 input pin differs')
            require(name not in shared or shared[name] == pin, 'A shared current39 input has inconsistent pins')
            shared[name] = pin
        program = entry['script']
        require(mapping['original38_program_pins'][phase] == {
            'script': program, 'original_RAW_sha256': original['input_files'][program]['sha256'],
            'canonical_Git_blob': entry['input_files'][program]['git_blob'],
            'host_transport': 'uniform_LF_or_CRLF_not_original_RAW_relabel'},
            'An original38 program pin was relabelled')
    return mapping


def require_sources(root, entry):
    for name, pin in entry['input_files'].items():
        raw = canonical_text((root / name).read_bytes())
        require(len(raw) == pin['bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
                and git_blob(raw) == pin['git_blob'],
                'A current39 Node direct/transitive canonical Git source differs')
