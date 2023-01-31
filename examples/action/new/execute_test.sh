mkdir -p results
rm -f test/*
irmasim -nr 20 -im agent.model --phase test options_test.json
python ../plotter.py -d new/test -r