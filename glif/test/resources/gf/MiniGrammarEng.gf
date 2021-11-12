concrete MiniGrammarEng of MiniGrammar = {
    lincat
        S = Str;
        NP = Str;
        VP = Str;
    lin
        everyone = "everyone";
        someone = "someone";
        love np = "loves" ++ np;
        hate np = "hates" ++ np;
        s np vp = np ++ vp;
        and a b = a ++ "and" ++ b;
}
