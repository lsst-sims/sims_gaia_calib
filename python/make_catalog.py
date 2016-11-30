#!/Users/yoachim/lsst/DarwinX86/miniconda2/3.19.0.lsst4/bin/python
import argparse
from gaia_spec import gen_gums_mag_cat

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate a catalog of GAIA magnitudes")
    parser.add_argument("--start_star", type=int, help="Star to start on")
    parser.add_argument("--nstars", type=int)
    parser.add_argument("--workdir", type=str, help="working directory")

    args = parser.parse_args()

    gen_gums_mag_cat(istart=args.start_star, nstars=args.nstars, workdir=args.workdir)
