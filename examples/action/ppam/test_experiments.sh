mkdir -p test
rm -f agent.model test/*
irmasim -nr 200 -im agent.model -om agent.model options_ppam_test.json
python ../plotter.py -d ppam/test -r -l