mkdir -p results
rm -f agent.model results/*
irmasim -nr 1 -im agent.model -om agent.model options_ppam_test.json
