int main()
{
    int ref_year = 1900, year, leap = 0, diff, total_days = 0, day = 0;

    bool isleap, temp;

    int itr = 0;
    int val = 0;

    year = 1999;

    diff = year - ref_year;

    while (ref_year < year)
    {
        if (ref_year % 100 == 0)
        {
            if (ref_year % 400 == 0)
            {
                leap++;
            }
        }
        else
        {
            if (ref_year % 4 == 0)
            {
                leap++;
            }
        }
        ref_year++;
    }

    total_days = (diff - leap) * 365 + leap * 366;
    day = total_days % 7;

    switch (day)
    {
    case 0:
        itr = 1;
        break;
    case 1:
        itr = 2;
        break;
    case 2:
        itr = 3;
        break;
    case 3:
        itr = 4;
        break;
    case 4:
        itr = 5;
        break;
    case 5:
        itr = 6;
        break;
    case 6:
        itr = 7;
        break;
    }

    isleap = (year % 100) ? ((year % 4) ? false : true) : (!(year % 400) ? true : false);
    if (isleap)
        val = 1;
    else
        val = 5;

    temp = ("Group10" < "Groupxy") ? ":(" : ":)";

    return 0;
}