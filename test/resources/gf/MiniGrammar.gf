abstract MiniGrammar = {
    cat
        S;
        NP;
        VP;
    fun
        everyone : NP;
        someone : NP;
        love : NP -> VP;
        hate : NP -> VP;
        s : NP -> VP -> S;
        and : S -> S -> S;
}
