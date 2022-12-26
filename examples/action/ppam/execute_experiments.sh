mkdir -p results
rm -f agent.model results/*
irmasim -nr 100 -im agent.model -om agent.model options_ppam.json
python ../plotter.py -d ppam/results -r -l
