import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from step4_ml.step4_ml_prediction import run_incremental_prediction


if __name__ == '__main__':
    run_incremental_prediction()
