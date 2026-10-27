from shared.catalog import suite_root

VOICES={
    'Femme · naturelle':('fr_FR-siwis-medium.onnx','641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99'),
    'Homme · naturelle':('fr_FR-tom-medium.onnx','bf65074ccdeeeeaa832e75edb1c0a513c01c9a972bdf085ff8a6e71ea234fd41'),
}

def installed_voices():return [label for label,(filename,_) in VOICES.items() if (suite_root()/'ergoai/voices'/filename).is_file()]
