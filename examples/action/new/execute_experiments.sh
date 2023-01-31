mkdir -p results
rm -f agent.model results/*
irmasim -nr 50 -im agent.model -om agent.model options.json
python ../plotter.py -d new/results -r -l