mkdir -p results
rm -f agent.model results/*
irmasim -nr 2 -im agent.model -om agent.model options_simple.json
python ../plotter.py -d simple/results -l -r
