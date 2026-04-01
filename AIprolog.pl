place('Portland').
place('Kingston').
place('St.thomas').
place('St.andrew').
place('St.mary').
place('St.Ann').
place('Trelawny').
place('St.James').
place('Hanover').
place('Westmoreland').
place('St.Elizabeth').
place('Manchester').
place('Clarendon').
place('St.Catherine').

% coordinates on SVG map (x,y) for 860x580 viewBox
% north coast = small y (top), south coast = large y (bottom)
% west = small x (left),       east = large x (right)
%
%  [Hanover][St.James][Trelawny][--St.Ann--][St.Mary ][Portland]   <- north coast
%  [Westmoreland]                                                   <- SW corner
%        [St.Elizabeth][Manchester][Clarendon][St.Catherine][Kingston][St.Thomas]
%                                                   [St.Andrew]     <- inland
coords('Hanover',      126, 204).
coords('Westmoreland', 115, 380).
coords('St.James',     175, 138).
coords('Trelawny',     268, 118).
coords('St.Ann',       390, 118).
coords('St.mary',      500, 155).
coords('Portland',     650, 222).
coords('St.andrew',    575, 312).
coords('Kingston',     585, 402).
coords('St.thomas',    715, 408).
coords('St.Catherine', 500, 356).
coords('Clarendon',    390, 392).
coords('Manchester',   308, 348).
coords('St.Elizabeth', 215, 362).


% road model
% road(From, To, DistanceKm, RoadType, Condition, PotholeDepthInches, TravelTimeMin, Status, Direction)
% RoadType: paved|unpaved
% Condition: none|'broken cistern'|'deep potholes'
% Status: open|closed|seasonal_blocked
% Direction: two_way|one_way

road('Portland','St.thomas',110,'unpaved','deep potholes',4,90,open,two_way).
road('Portland','St.mary',70.1,'paved','broken cistern',0,90,open,two_way).
road('St.thomas','St.andrew',51,'unpaved','none',0,60,open,two_way).
road('St.andrew','Kingston',8.5,'paved','none',0,30,open,two_way).
road('Kingston','St.Catherine',34.7,'paved','deep potholes',4,49,open,two_way).
road('St.Catherine','Clarendon',47.7,'paved','deep potholes',5,55,open,two_way).
road('St.andrew','St.mary',22,'paved','none',0,35,open,one_way).
road('St.mary','St.Ann',30,'paved','none',0,40,seasonal_blocked,two_way).
road('St.Catherine','St.andrew',30.0,'paved','deep potholes',5,00,open,two_way).



% condition mapping


avoid_condition('broken cistern', 'broken cistern').
avoid_condition('deep potholes', 'deep potholes').
avoid_condition('none', none).



% road cost filter


traversable_road(Current, Next, Dist, Type, Cond, Depth, Dur, Status) :-
    road(Current, Next, Dist, Type, Cond, Depth, Dur, Status, _).

traversable_road(Current, Next, Dist, Type, Cond, Depth, Dur, Status) :-
    road(Next, Current, Dist, Type, Cond, Depth, Dur, Status, two_way).

effective_condition('deep potholes', _, 'deep potholes') :- !.
effective_condition(_, Depth, 'deep potholes') :- Depth > 3, !.
effective_condition(Cond, _, Cond).


road_cost(Current, Next, Dist, NewDur, TypeChoice, AvoidOption) :-
    traversable_road(Current, Next, Dist, Type, Cond, Depth, Dur, Status),
    Status = open,

    % enforce road type
    Type = TypeChoice,

    % map avoid option
    avoid_condition(AvoidOption, AvoidCond),

    % filtering logic
    effective_condition(Cond, Depth, ActualCond),

    ( AvoidCond = none
    ; ActualCond \= AvoidCond
    ),

    adjust_duration(ActualCond, Dur, NewDur).



% dijstra adjustment


adjust_duration('deep potholes', Dur, NewDur) :-
    NewDur is Dur + 5.

adjust_duration('broken cistern', Dur, NewDur) :-
    NewDur is Dur + 5.

adjust_duration('none', Dur, Dur).



% dijkstra entry point


dijkstra(Start, End, Path, Distance, Duration, TypeChoice, AvoidOption) :-
    dijkstra_queue([(0, Start, [Start], 0)], End, RevPath, Distance, Duration, TypeChoice, AvoidOption),
    reverse(RevPath, Path).


% A* SEARCH

coord_distance(NodeA, NodeB, PixelDistance) :-
    coords(NodeA, X1, Y1),
    coords(NodeB, X2, Y2),
    DX is X1 - X2,
    DY is Y1 - Y2,
    PixelDistance is sqrt(DX * DX + DY * DY).

edge_km_per_pixel(Ratio) :-
    traversable_road(From, To, DistanceKm, _, _, _, _, _),
    coord_distance(From, To, PixelDistance),
    PixelDistance > 0,
    Ratio is DistanceKm / PixelDistance.

min_km_per_pixel(MinRatio) :-
    findall(R, edge_km_per_pixel(R), Ratios),
    Ratios \= [],
    min_list(Ratios, MinRatio).

heuristic(Node, Goal, H) :-
    coord_distance(Node, Goal, PixelDistance),
    min_km_per_pixel(MinRatio),
    H is PixelDistance * MinRatio,
    !.

heuristic(_, _, 0).

closed_has_better_or_equal(Node, G, Closed) :-
    member((Node, BestG), Closed),
    BestG =< G.

remove_closed_entry(_, [], []).
remove_closed_entry(Node, [(Node, _) | Rest], Rest) :- !.
remove_closed_entry(Node, [Head | Rest], [Head | UpdatedRest]) :-
    remove_closed_entry(Node, Rest, UpdatedRest).

update_closed(Node, G, Closed, [(Node, G) | UpdatedClosed]) :-
    remove_closed_entry(Node, Closed, UpdatedClosed).

astar(Start, End, Path, Distance, Duration, TypeChoice, AvoidOption) :-
    heuristic(Start, End, H0),
    astar_open([(H0, 0, Start, [Start], 0)], [], End, RevPath, Distance, Duration, TypeChoice, AvoidOption),
    reverse(RevPath, Path).

astar_open([( _, G, End, Path, Dur) | _], _, End, Path, G, Dur, _, _) :- !.

astar_open([( _, G, Current, Path, Dur) | RestOpen], Closed, End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption) :-
    ( closed_has_better_or_equal(Current, G, Closed) ->
        astar_open(RestOpen, Closed, End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption)
    ;
        findall(
            (F2, G2, Next, [Next | Path], Dur2),
            (
                road_cost(Current, Next, D, DurAdj, TypeChoice, AvoidOption),
                \+ member(Next, Path),
                G2 is G + D,
                Dur2 is Dur + DurAdj,
                heuristic(Next, End, H2),
                F2 is G2 + H2
            ),
            Children
        ),
        append(RestOpen, Children, OpenAfterExpand),
        sort(OpenAfterExpand, SortedOpen),
        update_closed(Current, G, Closed, UpdatedClosed),
        astar_open(SortedOpen, UpdatedClosed, End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption)
    ).







dijkstra_queue([(Dist, End, Path, Dur) | _], End, Path, Dist, Dur, _, _).

dijkstra_queue([(Dist, Current, Path, PrevDur) | Rest], End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption) :-

    findall(
        (NewDist, Next, [Next | Path], NewDurTotal),
        (
            road_cost(Current, Next, D, DurAdj, TypeChoice, AvoidOption),
            \+ member(Next, Path),
            NewDist is Dist + D,
            NewDurTotal is PrevDur + DurAdj
        ),
        Neighbors
    ),

    append(Rest, Neighbors, TempQueue),
    sort(TempQueue, SortedQueue),

    dijkstra_queue(SortedQueue, End, FinalPath, FinalDist, FinalDur, TypeChoice, AvoidOption).







add5(Newdur):-road(_,_,_,_,Cond,_,Dur,_,_),((Cond=='deep potholes';Cond=='broken cistern')->Newdur is Dur+5,nl,
       write('duration is upgraded, new duration is '),write(Newdur) ;Newdur is Dur+0).


findshortest(S,D,C,Dist):-write('enter start'),read(S),nl,write('enter destination: '),read(D),nl,
              write('enter conditions: '),read(C),
               
              road(S,D,Dist,_,C,_,_,_,_).
            
    

%add5:-road(_,_,_,pav,cond,Dur,_).

%DEPTH FIRST SEARCH (DFS)
% DFS entry point(With error handling)
dfs(Start, End, Path, Distance, Duration, TypeChoice, AvoidOption) :-
    dfs_search([Start], End, [Start], Path, 0, Distance, 0, Duration, TypeChoice, AvoidOption), !.

dfs(_, _, ['No path found'], 0, 0, _, _).

% DFS search base case: reached destination
dfs_search([End | _], End, Path, Path, Dist, Dist, Dur, Dur, _, _) :- !.

% DFS search recursive case
dfs_search([Current | Rest], End, Visited, Path, AccDist, FinalDist, AccDur, FinalDur, TypeChoice, AvoidOption) :-
    road_cost(Current, Next, D, DurAdj, TypeChoice, AvoidOption),
    \+ member(Next, Visited),
    NewDist is AccDist + D,
    NewDur is AccDur + DurAdj,
    dfs_search([Next | [Current | Rest]], End, [Next | Visited], Path, NewDist, FinalDist, NewDur, FinalDur, TypeChoice, AvoidOption).

% Backtrack if no valid neighbors
dfs_search([_ | Rest], End, Visited, Path, AccDist, FinalDist, AccDur, FinalDur, TypeChoice, AvoidOption) :-
    dfs_search(Rest, End, Visited, Path, AccDist, FinalDist, AccDur, FinalDur, TypeChoice, AvoidOption).
