for scheduler in minimal pareto; do
    rm -rf ${scheduler}/*
    irmasim  -o ${scheduler} options_${scheduler}.json
done
