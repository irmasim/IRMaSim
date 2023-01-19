mkdir -p test
rm -f test/*
irmasim -nr 20 -im agent.model --phase test options_ppam_test.json
python ../plotter.py -d ppam/test -r