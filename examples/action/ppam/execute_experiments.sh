mkdir -p results
rm -f agent.model results/*
irmasim -nr 10 -im agent.model -om agent.model options_ppam.json