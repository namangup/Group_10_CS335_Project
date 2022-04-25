// A sample systems program

int main(int argc, char *argv[])
{

    char pattern_string, file_path;
    int fd[2];

    if (argc < 4)
    {
        fprintf(stderr, "Invalid input.\n");
        fprintf(stderr, "Usage: dir_name [file] [command] \n");
        exit(0);
    }

    pattern_string = (char)argv[2];
    file_path = (char)argv[3];

    if (!(strcmp(argv[1], "@")))
    {
        unsigned int pid;
        // Implementing @ operator
        if (pipe(fd) < 0)
            perror("pipe");

        pid = fork();
        if (pid == 0)
        { // Child will run wc -l
            char *arguments[3];
            dup2(fd[0], 0); // as wc -l will take it's input from pipe
            close(fd[0]);
            close(fd[1]);
            arguments[0] = "wc";
            arguments[1] = "-l";
            arguments[2] = NULL;
            execvp("wc", arguments);
        }
        else
        {                   // Parent will run grep command
            dup2(fd[1], 1); // as grep -rF will push it's output to pipe
            close(fd[1]);
            close(fd[0]);
        }
    }
    return 0;
}
