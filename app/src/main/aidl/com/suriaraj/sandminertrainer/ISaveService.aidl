package com.suriaraj.sandminertrainer;

interface ISaveService {
    void destroy() = 16777114;
    String getState() = 1;
    String applyValues(int money, int gems) = 2;
    String restoreLatest() = 3;
}
