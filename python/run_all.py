from gaia_spec import *




# Generate the GAIA response function, assume there's a single 16th mag WD that we're calibrating to
make_response_func(magnorm=10.)
make_response_func(magnorm=10., noise=0, savefile='gaia_response_nonoise.npz')

# Generate spectra for all the stars
#gen_gums_mag_cat(istart=0, nstars=1000, workdir='test1')
# XXX-nope cat calls.sh | xargs -n19 -I'{}' -P7  bash -c '{}'

#  ./make_catalog.py --start_star 0 --nstars 11027 --workdir central_raft
#  ./make_catalog.py --start_star 0 --nstars 26187 --workdir full_field
#  ./make_catalog.py --start_star 0 --nstars 33578 --workdir full_field