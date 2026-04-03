% Consolidated place data: place_info(Name, Type, X, Y)
place_info('Portland',     parish, 650, 222).
place_info('Kingston',     city,   585, 402).
place_info('St.thomas',    parish, 715, 408).
place_info('St.andrew',    parish, 575, 312).
place_info('St.mary',      parish, 500, 155).
place_info('St.Ann',       parish, 390, 118).
place_info('Trelawny',     parish, 268, 118).
place_info('St.James',     parish, 175, 138).
place_info('Hanover',      parish, 126, 204).
place_info('Westmoreland', parish, 115, 380).
place_info('St.Elizabeth', parish, 215, 362).
place_info('Manchester',   parish, 308, 348).
place_info('Clarendon',    parish, 390, 392).
place_info('St.Catherine', parish, 500, 356).

% Helper predicates to maintain backward compatibility
place(Name) :- place_info(Name, _, _, _).
place_type(Name, Type) :- place_info(Name, Type, _, _).
coords(Name, X, Y) :- place_info(Name, _, X, Y).


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
road('Clarendon','Manchester',60.0,'paved','broken cistern',0,35,open,two_way).
road('Manchester','St.Elizabeth',40.0,'paved','broken cistern',0,40,open,two_way).
road('St.andrew','St.mary',22,'paved','none',0,35,open,one_way).
road('St.mary','St.Ann',30,'paved','none',0,40,seasonal_blocked,two_way).
road('St.Catherine','St.andrew',30.0,'paved','deep potholes',5,00,open,two_way).
road('St.Elizabeth','Hanover',50.0,'paved','broken cistern',0,60,open,two_way).



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
% DFS entry point (returns first valid path, not guaranteed shortest)
dfs(Start, End, Path, Distance, Duration, TypeChoice, AvoidOption) :-
    dfs_path(Start, End, [Start], RevPath, TypeChoice, AvoidOption),
    !,
    reverse(RevPath, Path),
    path_totals(Path, Distance, Duration, TypeChoice, AvoidOption).

dfs(_, _, ['No path found'], 0, 0, _, _).

% DFS path search base case
dfs_path(End, End, Visited, Visited, _, _) :- !.

% DFS path search recursive case
dfs_path(Current, End, Visited, Path, TypeChoice, AvoidOption) :-
    road_cost(Current, Next, _, _, TypeChoice, AvoidOption),
    \+ member(Next, Visited),
    dfs_path(Next, End, [Next | Visited], Path, TypeChoice, AvoidOption).

% Compute total distance and duration for a path
path_totals([_], 0, 0, _, _) :- !.

path_totals([From, To | Rest], TotalDist, TotalDur, TypeChoice, AvoidOption) :-
    road_cost(From, To, Dist, DurAdj, TypeChoice, AvoidOption),
    path_totals([To | Rest], RestDist, RestDur, TypeChoice, AvoidOption),
    TotalDist is Dist + RestDist,
    TotalDur is DurAdj + RestDur.
