mkdir -p test
irmasim -nr 50 -im agent.model --phase test options_ppam_test.json
python ../plotter.py -d ppam/test -r